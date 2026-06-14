import unittest
import os
import pandas as pd
from src.generator.excel import generate_excel_report
from src.generator.timeline import generate_gantt_chart

class TestGenerators(unittest.TestCase):
    def setUp(self):
        self.roadmap_data = {
            "projects": {
                "nodes": [
                    {
                        "name": "Project Alpha",
                        "startDate": "2026-05-31",
                        "targetDate": "2026-07-13",
                        "state": "started",
                        "milestones": {
                            "nodes": [
                                {"name": "Kickoff", "targetDate": "2026-06-01"},
                                {"name": "Beta Release", "targetDate": "2026-07-01"}
                            ]
                        },
                        "issues": {
                            "nodes": [
                                {
                                    "title": "Task 1",
                                    "status": {"name": "Started"},
                                    "dueDate": "2026-06-15",
                                    "assignee": {"name": "Brian"}
                                },
                                {
                                    "title": "Task 2",
                                    "status": None,
                                    "dueDate": None,
                                    "assignee": None
                                }
                            ]
                        }
                    }
                ]
            }
        }
        self.excel_output = "/tmp/test_roadmap.xlsx"
        self.gantt_output = "/tmp/test_roadmap.png"

    def tearDown(self):
        # Clean up output files
        for f in [self.excel_output, self.gantt_output]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

    def test_excel_generation(self):
        generate_excel_report(self.roadmap_data, self.excel_output)
        self.assertTrue(os.path.exists(self.excel_output))
        
        # Read the file back with pandas to verify structure
        df_p = pd.read_excel(self.excel_output, sheet_name="Projects & Milestones")
        df_i = pd.read_excel(self.excel_output, sheet_name="Actionable Issues")
        
        self.assertEqual(len(df_p), 1)
        self.assertEqual(df_p.iloc[0]["Project Name"], "Project Alpha")
        
        self.assertEqual(len(df_i), 2)
        self.assertEqual(df_i.iloc[0]["Assignee"], "Brian")
        # Checking that empty fields fallback correctly
        self.assertEqual(df_i.iloc[1]["Assignee"], "Unassigned")
        self.assertEqual(df_i.iloc[1]["Status"], "Unknown")

        # Verify the presence of the Visual Roadmap sheet
        with pd.ExcelFile(self.excel_output) as excel_file:
            self.assertIn("Visual Roadmap", excel_file.sheet_names)

    def test_gantt_chart_generation(self):
        generate_gantt_chart(self.roadmap_data, self.gantt_output)
        self.assertTrue(os.path.exists(self.gantt_output))
        self.assertGreater(os.path.getsize(self.gantt_output), 0)
