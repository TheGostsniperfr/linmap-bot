import logging
import pandas as pd
from typing import Dict, Any, List
import os

logger = logging.getLogger(__name__)

def generate_excel_report(roadmap_data: Dict[str, Any], output_path: str) -> None:
    """
    Parses Linear GraphQL JSON payload into a structured three-sheet Excel workbook.
    Ensures correct styling, headers, cell borders, gridlines, and column widths.
    Includes automated Excel Tables and a Visual Roadmap Gantt chart.
    """
    logger.info(f"Starting Excel report generation at: {output_path}")
    
    projects_list = roadmap_data.get("projects", {}).get("nodes", []) or []
    if not projects_list:
        logger.warning("No project data provided to generate Excel report. Creating empty sheets.")
        df_projects = pd.DataFrame(columns=["Project Name", "State", "Target Date"])
        df_issues = pd.DataFrame(columns=["Project Context", "Issue Title", "Status", "Due Date", "Assignee"])
    else:
        project_rows = []
        issues_rows = []

        for proj in projects_list:
            if not proj:
                continue
            project_rows.append({
                "Project Name": proj.get("name", ""),
                "State": proj.get("state", ""),
                "Target Date": proj.get("targetDate", "") or "TBD",
            })
            
            # Parse associated issues
            issues = proj.get("issues", {}).get("nodes", []) or []
            for issue in issues:
                if not issue:
                    continue
                issues_rows.append({
                    "Project Context": proj.get("name", ""),
                    "Issue Title": issue.get("title", ""),
                    "Status": issue.get("status", {}).get("name") if issue.get("status") else "Unknown",
                    "Due Date": issue.get("dueDate", "") or "TBD",
                    "Assignee": issue.get("assignee", {}).get("name") if issue.get("assignee") else "Unassigned"
                })

        df_projects = pd.DataFrame(project_rows)
        df_issues = pd.DataFrame(issues_rows)

    try:
        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            workbook = writer.book
            
            # Format Definitions
            header_format = workbook.add_format({
                "bold": True,
                "text_wrap": True,
                "valign": "vcenter",
                "align": "center",
                "fg_color": "#1B365D",
                "font_color": "white",
                "border": 1,
                "border_color": "#D3D3D3"
            })
            
            data_format = workbook.add_format({
                "border": 1,
                "border_color": "#D3D3D3",
                "valign": "vcenter"
            })
            
            date_format = workbook.add_format({
                "border": 1,
                "border_color": "#D3D3D3",
                "valign": "vcenter",
                "num_format": "yyyy-mm-dd",
                "align": "center"
            })
            
            # Helper to write sheet and apply styles row-by-row
            def write_sheet(df: pd.DataFrame, sheet_name: str) -> None:
                logger.info(f"Writing sheet: {sheet_name}")
                worksheet = workbook.add_worksheet(sheet_name)
                # Register sheet in writer's sheets dict for compatibility
                writer.sheets[sheet_name] = worksheet
                
                # Write data rows (data starts at row 1 because header is at row 0)
                for row_num, row_data in enumerate(df.values):
                    for col_num, val in enumerate(row_data):
                        col_name = df.columns[col_num]
                        is_date = "date" in col_name.lower() or "due" in col_name.lower() or "target" in col_name.lower()
                        
                        # Format dates if valid
                        if is_date and pd.notna(val) and val not in ("", "TBD"):
                            worksheet.write(row_num + 1, col_num, val, date_format)
                        else:
                            write_val = "" if pd.isna(val) else val
                            worksheet.write(row_num + 1, col_num, write_val, data_format)
                
                # Format as Excel Table if not empty to provide sort filters and banded rows
                if not df.empty:
                    columns_option = [{"header": col} for col in df.columns]
                    worksheet.add_table(0, 0, len(df), len(df.columns) - 1, {
                        "columns": columns_option,
                        "style": "Table Style Medium 2"
                    })
                else:
                    # Write headers manually if empty
                    for col_num, header in enumerate(df.columns):
                        worksheet.write(0, col_num, header, header_format)
                
                # Formatting details
                worksheet.set_row(0, 26)  # Set header row height
                worksheet.hide_gridlines(2)  # Force gridlines to display
                
                # Auto-fit columns dynamically
                for i, col in enumerate(df.columns):
                    max_val_len = df[col].astype(str).map(len).max() if not df.empty else 0
                    max_len = max(max_val_len, len(col)) + 4
                    worksheet.set_column(i, i, max_len)
            
            write_sheet(df_projects, "Projects & Milestones")
            write_sheet(df_issues, "Actionable Issues")
            
            # --- 3. NEW SHEET: Visual Roadmap ---
            logger.info("Generating Visual Roadmap (Excel Gantt) sheet...")
            gantt_sheet = workbook.add_worksheet("Visual Roadmap")
            writer.sheets["Visual Roadmap"] = gantt_sheet
            
            # Visual Roadmap formatting
            gantt_header_format_no_rotate = workbook.add_format({
                "bold": True,
                "text_wrap": True,
                "valign": "vcenter",
                "align": "center",
                "fg_color": "#1B365D",
                "font_color": "white",
                "border": 1,
                "border_color": "#D3D3D3"
            })
            
            gantt_header_format_rotated = workbook.add_format({
                "bold": True,
                "valign": "vcenter",
                "align": "center",
                "fg_color": "#1B365D",
                "font_color": "white",
                "border": 1,
                "border_color": "#D3D3D3",
                "rotation": 90
            })
            
            gantt_label_format = workbook.add_format({
                "bold": True,
                "valign": "vcenter",
                "border": 1,
                "border_color": "#D3D3D3"
            })
            
            gantt_empty_format = workbook.add_format({
                "border": 1,
                "border_color": "#F0F0F0",
                "bg_color": "#FFFFFF"
            })
            
            # Status styling formats
            status_formats = {
                "started": workbook.add_format({
                    "bg_color": "#80CBC4",  # Teal accent
                    "border": 1,
                    "border_color": "#D3D3D3"
                }),
                "backlog": workbook.add_format({
                    "bg_color": "#C5CAE9",  # Indigo/Slate accent
                    "border": 1,
                    "border_color": "#D3D3D3"
                }),
                "paused": workbook.add_format({
                    "bg_color": "#FFE082",  # Orange accent
                    "border": 1,
                    "border_color": "#D3D3D3"
                }),
                "planned": workbook.add_format({
                    "bg_color": "#FFCDD2",  # Light Red/Crimson accent
                    "border": 1,
                    "border_color": "#D3D3D3"
                })
            }
            default_status_format = workbook.add_format({
                "bg_color": "#E0E0E0",
                "border": 1,
                "border_color": "#D3D3D3"
            })
            
            # Calculate timeline range bounds
            project_dates: List[pd.Timestamp] = []
            for proj in projects_list:
                if not proj:
                    continue
                start = proj.get("startDate")
                target = proj.get("targetDate")
                if start and start != "TBD":
                    try:
                        project_dates.append(pd.to_datetime(start))
                    except Exception as e:
                        logger.debug(f"Failed to parse startDate '{start}': {e}")
                if target and target != "TBD":
                    try:
                        project_dates.append(pd.to_datetime(target))
                    except Exception as e:
                        logger.debug(f"Failed to parse targetDate '{target}': {e}")
                        
            if project_dates:
                min_date = min(project_dates)
                max_date = max(project_dates)
            else:
                min_date = pd.to_datetime("2026-05-31")
                max_date = pd.to_datetime("2026-08-31")
                
            # Align boundaries to week start (Monday) and week end (Sunday)
            start_date_aligned = min_date - pd.Timedelta(days=min_date.dayofweek)
            end_date_aligned = max_date + pd.Timedelta(days=6 - max_date.dayofweek)
            
            # Generate weekly columns starting from Column C
            weeks = pd.date_range(start=start_date_aligned, end=end_date_aligned, freq="W-MON")
            
            # Freeze panes so headers and labels remain visible during scroll
            gantt_sheet.freeze_panes(1, 2)
            gantt_sheet.set_row(0, 70)  # Make space for rotated vertical headers
            gantt_sheet.set_column(0, 0, 30)  # Project Name
            gantt_sheet.set_column(1, 1, 15)  # Status
            
            if len(weeks) > 0:
                gantt_sheet.set_column(2, 2 + len(weeks) - 1, 3)  # Narrow timeline columns
                
            # Write headers
            gantt_sheet.write(0, 0, "Project Name", gantt_header_format_no_rotate)
            gantt_sheet.write(0, 1, "Status", gantt_header_format_no_rotate)
            for col_idx, week_start in enumerate(weeks):
                date_str = week_start.strftime("%Y-%m-%d")
                gantt_sheet.write(0, 2 + col_idx, date_str, gantt_header_format_rotated)
                
            # Write rows
            for row_idx, proj in enumerate(projects_list):
                if not proj:
                    continue
                proj_name = proj.get("name", "Unnamed Project")
                proj_status = proj.get("state", "backlog") or "backlog"
                
                gantt_sheet.set_row(row_idx + 1, 20)
                gantt_sheet.write(row_idx + 1, 0, proj_name, gantt_label_format)
                gantt_sheet.write(row_idx + 1, 1, proj_status.title(), gantt_label_format)
                
                proj_start_str = proj.get("startDate")
                proj_target_str = proj.get("targetDate")
                
                proj_start = None
                proj_target = None
                try:
                    if proj_start_str and proj_start_str != "TBD":
                        proj_start = pd.to_datetime(proj_start_str)
                    else:
                        proj_start = start_date_aligned
                except:
                    proj_start = start_date_aligned
                    
                try:
                    if proj_target_str and proj_target_str != "TBD":
                        proj_target = pd.to_datetime(proj_target_str)
                except:
                    pass
                
                for col_idx, week_start in enumerate(weeks):
                    week_end = week_start + pd.Timedelta(days=6)
                    is_active = False
                    
                    if proj_start and proj_target:
                        is_active = (max(proj_start, week_start) <= min(proj_target, week_end))
                    elif proj_start and not proj_target:
                        is_active = (week_start <= proj_start <= week_end)
                        
                    if is_active:
                        fmt = status_formats.get(proj_status, default_status_format)
                        gantt_sheet.write(row_idx + 1, 2 + col_idx, "", fmt)
                    else:
                        gantt_sheet.write(row_idx + 1, 2 + col_idx, "", gantt_empty_format)
            
            gantt_sheet.hide_gridlines(2)  # Force gridlines to display
            
        logger.info("Excel report generated successfully.")
    except Exception as e:
        logger.error(f"Failed to compile Excel workbook: {e}")
        raise
