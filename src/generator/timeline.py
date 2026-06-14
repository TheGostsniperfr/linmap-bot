import logging
import pandas as pd
import plotly.graph_objects as go
import re
import base64
import os
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Original vibrant colors for optimal visibility
THEMES = [
    {"name": "Phase 1", "left_bg": "#E83E60", "lane_bg": "#FCE2E6", "bar_bg": "#E83E60"},
    {"name": "Phase 2", "left_bg": "#56A8B9", "lane_bg": "#D1EBEF", "bar_bg": "#56A8B9"},
    {"name": "Phase 3", "left_bg": "#F39C12", "lane_bg": "#FDEED2", "bar_bg": "#F39C12"},
    {"name": "Phase 4", "left_bg": "#00839B", "lane_bg": "#CFF2FA", "bar_bg": "#00839B"},
]

def draw_chevron_bar(fig: go.Figure, x_start: str, x_end: str, y_center: float, 
                     height: float, color: str, text: str, 
                     is_first: bool = False, is_last: bool = False) -> None:
    """
    Draws a stylized chevron representing a project phase or milestone range.
    
    Generates a custom SVG path to represent a chevron/arrow bar on a Plotly figure.
    Positions text intelligently inside or to the right of the shape depending on
    the task duration to optimize readability.
    
    Args:
        fig: The Plotly Figure object to draw on.
        x_start: Start date string (YYYY-MM-DD) of the phase.
        x_end: End date string (YYYY-MM-DD) of the phase.
        y_center: Vertical coordinate center for the lane/bar.
        height: Height/thickness of the chevron bar.
        color: Hex color string to fill the chevron shape.
        text: Label text to display on or next to the chevron.
        is_first: True if this is the start of the overall timeline (removes indent on the left side).
        is_last: True if this is the end of the overall timeline (removes indent on the right side).
    """
    start_dt = pd.to_datetime(x_start)
    end_dt = pd.to_datetime(x_end)
    duration_days = (end_dt - start_dt).days
    
    # Geometric safety checks
    arrow_width_days = min(4.0, max(0.1, duration_days / 2.5))
    arrow_width = pd.Timedelta(days=arrow_width_days)
    
    x0 = start_dt.strftime("%Y-%m-%d")
    x0_indent = (start_dt + arrow_width).strftime("%Y-%m-%d")
    x1 = end_dt.strftime("%Y-%m-%d")
    x1_indent = (end_dt - arrow_width).strftime("%Y-%m-%d")
    
    y_top = y_center - (height / 2)
    y_bot = y_center + (height / 2)
    
    # SVG Path
    if is_first and is_last:
        path = f"M {x0},{y_top} L {x1},{y_top} L {x1},{y_bot} L {x0},{y_bot} Z"
    elif is_first:
        path = f"M {x0},{y_top} L {x1_indent},{y_top} L {x1},{y_center} L {x1_indent},{y_bot} L {x0},{y_bot} Z"
    elif is_last:
        path = f"M {x0},{y_top} L {x1},{y_top} L {x1},{y_bot} L {x0},{y_bot} L {x0_indent},{y_center} Z"
    else:
        path = f"M {x0},{y_top} L {x1_indent},{y_top} L {x1},{y_center} L {x1_indent},{y_bot} L {x0},{y_bot} L {x0_indent},{y_center} Z"

    # Shadow
    shadow_path = path.replace(str(y_top), str(y_top + 0.3)).replace(str(y_bot), str(y_bot + 0.3)).replace(str(y_center), str(y_center + 0.3))
    fig.add_shape(type="path", path=shadow_path, fillcolor="rgba(0,0,0,0.15)", line_width=0, layer="below")
    
    # Main bar
    fig.add_shape(type="path", path=path, fillcolor=color, line_width=0, layer="above")
    
    # Intelligent text positioning (optimal readability)
    if duration_days < 25:
        # Too short -> Text shifted to the right (allows up to 65 characters since it's outside the chevron)
        display_text = text if len(text) < 65 else text[:62] + "..."
        fig.add_annotation(
            x=(end_dt + pd.Timedelta(days=2)).strftime("%Y-%m-%d"),
            y=y_center,
            text=f"<b>{display_text}</b>",
            showarrow=False, font=dict(color="#1E293B", size=12, family="Arial"), xanchor="left"
        )
    else:
        # Long enough -> Center-aligned white text (truncated to 35 characters to not overflow chevron tips)
        display_text = text if len(text) < 35 else text[:32] + "..."
        center_dt = start_dt + (end_dt - start_dt) / 2
        fig.add_annotation(
            x=center_dt.strftime("%Y-%m-%d"),
            y=y_center,
            text=f"<b>{display_text}</b>",
            showarrow=False, font=dict(color="white", size=13, family="Arial"), xanchor="center"
        )

def draw_flag(fig: go.Figure, date_str: str, text: str, y_pos: float) -> None:
    """
    Draws a global program milestone marker at the top of the Gantt chart.
    
    Places a triangle-down marker at the specified date, displays the formatted
    milestone text, and draws a vertical dotted reference line extending down through
    the chart grid.
    
    Args:
        fig: The Plotly Figure object to draw on.
        date_str: Target date string (YYYY-MM-DD) of the milestone.
        text: Name or description of the global milestone.
        y_pos: Vertical positioning height for the flag marker itself.
    """
    date_dt = pd.to_datetime(date_str)
    date_formatted = date_dt.strftime("%d %b")
    
    # Vertical reference line descending to the beginning of the first phase (Y=5)
    fig.add_shape(type="line", x0=date_str, x1=date_str, y0=y_pos, y1=5, line=dict(color="#CBD5E1", width=1.5, dash="dot"))
    
    # Flag
    fig.add_trace(go.Scatter(
        x=[date_str], y=[y_pos],
        mode="markers+text", marker=dict(symbol="triangle-down", size=14, color="#008CD3"), # Harmonized with the logo blue
        text=[f"<b>{text} ({date_formatted})</b>"], textposition="top center",
        textfont=dict(color="#0F172A", size=11, family="Arial"), showlegend=False, hoverinfo="skip"
    ))

def generate_gantt_chart(roadmap_data: Dict[str, Any], output_path: str, months_zoom: Optional[int] = None) -> None:
    """
    Renders an executive PowerPoint-style Gantt chart from Linear roadmap data.
    
    Extracts projects, milestones, and issues, groups them by project, sorts them,
    and draws individual lanes (swimlanes). Renders chevron bars for phases, diamond markers
    for issue deliverables, and global milestone flags. Optionally applies a temporal zoom
    starting from today. The resulting chart is saved as a high-resolution PNG.
    
    Args:
        roadmap_data: GraphQL payload dictionary fetched from Linear containing projects,
            milestones, and issues.
        output_path: Local filesystem path where the rendered PNG image should be saved.
        months_zoom: Optional number of months to display forward from today's date.
            If None, the timeline encompasses all project dates.
            
    Raises:
        OSError: If directory creation or saving the image to disk fails.
        Exception: For general Plotly or Kaleido rendering errors.
    """
    logger.info(f"Starting Executive PowerPoint style Gantt rendering at: {output_path}")
    projects_raw = roadmap_data.get("projects", {}).get("nodes", []) or []
    
    valid_projects = []
    global_flags = []
    
    for p in projects_raw:
        if not p: continue
        start = p.get("startDate") or "2026-06-01"
        target = p.get("targetDate")
        if not target or target == "TBD":
            continue
        
        # Intercept global "Major Dates" (milestones of the GLOBAL project)
        if "GLOBAL" in p.get("name", "").upper():
            milestones = p.get("milestones", {}).get("nodes", []) or []
            for ms in milestones:
                ms_date = ms.get("targetDate")
                if ms_date and ms_date != "TBD":
                    global_flags.append({
                        "date": ms_date,
                        "name": ms.get("name", "")
                    })
            continue
            
        valid_projects.append({**p, "parsed_start": start, "parsed_target": target})
        
    if not valid_projects:
        logger.warning("No visual data found. Gantt generation skipped.")
        return

    # Sort phases by name (Phase 1, Phase 2, etc.)
    valid_projects.sort(key=lambda x: x.get("name", ""))

    ROW_HEIGHT = 4
    MARGIN_Y = 1.5
    fig = go.Figure()
    current_y = 5  # Safety margin at top for milestone flags
    all_dates = []

    # Process each project lane
    for i, proj in enumerate(valid_projects):
        theme_idx = i % len(THEMES)
        theme = THEMES[theme_idx]
        
        milestones = proj.get("milestones", {}).get("nodes", []) or []
        valid_milestones = [m for m in milestones if m.get("targetDate") and m.get("targetDate") != "TBD"]
        valid_milestones.sort(key=lambda x: pd.to_datetime(x["targetDate"]))
        
        num_rows = max(len(valid_milestones), 1)
        lane_height = (num_rows * ROW_HEIGHT) + (MARGIN_Y * 2)
        
        proj_start = pd.to_datetime(proj["parsed_start"])
        proj_end = pd.to_datetime(proj["parsed_target"])
        all_dates.extend([proj_start, proj_end])
        
        # Lane background (pastel)
        fig.add_shape(type="rect", xref="paper", yref="y", x0=0, x1=1, y0=current_y, y1=current_y + lane_height, fillcolor=theme["lane_bg"], line_width=0, layer="below")
        
        # Left title block layout
        fig.add_shape(type="rect", xref="paper", yref="y", x0=0, x1=0.10, y0=current_y, y1=current_y + lane_height, fillcolor=theme["left_bg"], line_width=1, line_color="white", layer="above")
        
        # Remove 'Phase X' prefixes from names
        raw_name = proj.get("name", theme["name"])
        clean_name = re.sub(r'(?i)^phase\s*\d+\s*:\s*', '', raw_name)
        
        # Wrap title text to fit within column C bounds
        words = clean_name.split()
        lines = []
        curr_line = []
        for w in words:
            if len(" ".join(curr_line + [w])) > 10:
                lines.append(" ".join(curr_line))
                curr_line = [w]
            else:
                curr_line.append(w)
        if curr_line:
            lines.append(" ".join(curr_line))
        wrapped_name = "<br>".join(lines)
        
        fig.add_annotation(xref="paper", yref="y", x=0.05, y=current_y + (lane_height / 2), text=f"<b>{wrapped_name}</b>", showarrow=False, font=dict(color="white", size=14, family="Arial"), xanchor="center")
        
        if not valid_milestones:
            draw_chevron_bar(fig, proj_start.strftime("%Y-%m-%d"), proj_end.strftime("%Y-%m-%d"), current_y + (lane_height / 2), ROW_HEIGHT - 1, theme["bar_bg"], proj.get("name", "Execution"), True, True)
        else:
            last_end = proj_start
            for m_idx, ms in enumerate(valid_milestones):
                ms_end = pd.to_datetime(ms["targetDate"])
                all_dates.append(ms_end)
                bar_y_center = current_y + MARGIN_Y + (ROW_HEIGHT / 2) + (m_idx * ROW_HEIGHT)
                
                if (ms_end - last_end).days < 2: ms_end = last_end + pd.Timedelta(days=3)
                
                draw_chevron_bar(fig, last_end.strftime("%Y-%m-%d"), ms_end.strftime("%Y-%m-%d"), bar_y_center, ROW_HEIGHT - 0.8, theme["bar_bg"], ms.get("name", ""), m_idx == 0, m_idx == len(valid_milestones) - 1)
                
                # Draw deliverables (diamonds)
                issues = proj.get("issues", {}).get("nodes", []) or []
                for issue in issues:
                    if not issue: continue
                    due_date = issue.get("dueDate")
                    if due_date and due_date != "TBD":
                        issue_dt = pd.to_datetime(due_date)
                        if last_end <= issue_dt <= ms_end:
                            fig.add_trace(go.Scatter(
                                x=[issue_dt.strftime("%Y-%m-%d")], y=[bar_y_center + (ROW_HEIGHT/2.5)],
                                mode="markers", marker=dict(symbol="diamond", size=10, color="#2563EB", line=dict(color="white", width=1)),
                                name="Deliverable", hovertext=issue.get("title", "Deliverable"), hoverinfo="text", showlegend=False
                            ))
                last_end = ms_end

        fig.add_shape(type="line", xref="paper", yref="y", x0=0, x1=1, y0=current_y + lane_height, y1=current_y + lane_height, line=dict(color="white", width=3), layer="above")
        current_y += lane_height

    # Calculate chart range
    today_dt = datetime.now()
    today_str = today_dt.strftime("%Y-%m-%d")
    
    if months_zoom is not None:
        # Start view from today, project N months forward
        min_date = today_str
        max_date = (today_dt + pd.Timedelta(days=months_zoom * 30.5)).strftime("%Y-%m-%d")
        logger.info(f"Zooming timeline from today ({min_date}) to {months_zoom} months forward ({max_date}).")
    else:
        # Default view encompassing all history
        min_date = (min(all_dates) - pd.Timedelta(days=15)).strftime("%Y-%m-%d")
        max_date = (max(all_dates) + pd.Timedelta(days=30)).strftime("%Y-%m-%d")

    # Draw milestone flags
    global_flags.sort(key=lambda x: pd.to_datetime(x["date"]))
    for idx, flag in enumerate(global_flags):
        # Alternation based on height settings: Y=1.3 or Y=4.5
        y_pos = 1.3 if idx % 2 == 0 else 4.5
        draw_flag(fig, flag["date"], flag["name"], y_pos)

    # Draw vertical month boundaries
    month_range = pd.date_range(start=min_date, end=max_date, freq="MS")
    for m_start in month_range:
        m_str = m_start.strftime("%Y-%m-%d")
        fig.add_shape(
            type="line", x0=m_str, x1=m_str, y0=5, y1=current_y,
            line=dict(color="rgba(148, 163, 184, 0.25)", width=1.5, dash="solid"),
            layer="above"
        )

    # Highlight August holiday period
    timeline_years = list(set([pd.to_datetime(d).year for d in all_dates]))
    for yr in timeline_years:
        aug_start = f"{yr}-08-01"
        aug_end = f"{yr}-09-01"
        fig.add_shape(
            type="rect", x0=aug_start, x1=aug_end, y0=5, y1=current_y,
            fillcolor="rgba(148, 163, 184, 0.20)", line_width=0, layer="below"
        )

    # Draw current date line
    if min_date <= today_str <= max_date:
        fig.add_shape(
            type="line", x0=today_str, x1=today_str, y0=5, y1=current_y,
            line=dict(color="#DC2626", width=2, dash="dot"),
            layer="above"
        )
        # Draw today's date label
        today_label = today_dt.strftime("%d %b")
        fig.add_annotation(
            x=today_str, y=4.8,
            text=f"<span style='color:#DC2626'><b>{today_label}</b></span>",
            showarrow=False, font=dict(size=11, family="Arial"),
            xanchor="center", yanchor="bottom"
        )

    # Configure chart layout and axes
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=30, r=30, t=220, b=40),
        xaxis=dict(
            domain=[0.105, 1.0], side="top", showgrid=False,
            tickformat="%b\n%Y", dtick="M1", tickfont=dict(size=16, color="#64748B", family="Arial", weight="bold"),
            linecolor="#008CD3", linewidth=4, range=[min_date, max_date], zeroline=False
        ),
        yaxis=dict(visible=False, autorange="reversed", range=[current_y, 0])
    )

    # Title
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.0, y=1.20,
        text="<span style='color:#1C3B4E'>PROJECT</span> <span style='color:#008CD3'>ROADMAP</span>",
        showarrow=False, font=dict(size=42, family="Arial Black, Impact, sans-serif"), xanchor="left"
    )
    
    fig.add_shape(
        type="rect", xref="paper", yref="paper", x0=0.0, x1=0.12, y0=1.13, y1=1.14, fillcolor="#008CD3", line_width=0
    )

    fig.add_shape(
        type="rect", xref="paper", yref="paper", x0=0.105, x1=1.0, y0=1.00, y1=1.08, fillcolor="#F1F5F9", line_width=0, layer="below"
    )

    # Embed brand logo
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.png")
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            fig.add_layout_image(
                dict(
                    source=f"data:image/png;base64,{encoded_string}",
                    xref="paper", yref="paper",
                    x=1.0, y=1.15,  # Vertically aligned with the title baseline
                    sizex=0.25, sizey=0.25,
                    xanchor="right", yanchor="middle"
                )
            )
            logger.info("DockAir logo embedded successfully into the chart.")
        except Exception as img_err:
            logger.warning(f"Could not encode or embed logo image: {img_err}")
    else:
        logger.warning(f"DockAir logo file not found at: {logo_path}. Skipping image render.")

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.write_image(output_path, width=1920, height=1080, scale=2, engine="kaleido")
        logger.info("Executive PowerPoint style timeline rendering completed successfully.")
    except Exception as e:
        logger.error(f"Visual rendering process failed: {e}")
        raise