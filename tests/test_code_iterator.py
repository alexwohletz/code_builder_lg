import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from langgraph_code_generator.agents.code_iterator import CodeIteratorAgent

class TestCodeIteratorAgent(unittest.TestCase):
    def setUp(self):
        self.iterator = CodeIteratorAgent()
        # Sample XML state with test results - includes all required sections
        self.test_state = {
            "xml_state": """
            <code_project>
                <metadata>
                    <project_name>TestProject</project_name>
                    <description>Test CSV Processing Application</description>
                    <author>Test Author</author>
                    <creation_date>2024-01-01</creation_date>
                </metadata>
                <planning>
                    <requirements>
                        <requirement id="req1">Handle CSV processing.</requirement>
                    </requirements>
                    <modules>
                        <module id="mod1">
                            <name>CSVProcessor</name>
                            <description>Process CSV files</description>
                            <dependencies>
                                <dependency>pandas</dependency>
                            </dependencies>
                        </module>
                    </modules>
                    <file_structure>
                        <file>
                            <file_name>csv_processor.py</file_name>
                            <module>CSVProcessor</module>
                            <purpose>Process CSV files</purpose>
                        </file>
                    </file_structure>
                </planning>
                <generation>
                    <files>
                        <file>
                            <file_name>csv_processor.py</file_name>
                            <file_path>src/csv_processor.py</file_path>
                            <file_contents><![CDATA[
                            def process_csv(file_path):
                                pass
                            ]]></file_contents>
                            <dependencies>
                                <dependency>pandas</dependency>
                            </dependencies>
                        </file>
                    </files>
                    <test_suite>
                        <suite_name>CSVProcessorTests</suite_name>
                        <test_files>
                            <test_file>
                                <test_file_name>test_csv_processor.py</test_file_name>
                                <test_file_path>tests/test_csv_processor.py</test_file_path>
                                <tests>
                                    <test>
                                        <test_name>test_empty_file</test_name>
                                        <test_description>Test handling of empty CSV files</test_description>
                                        <test_code><![CDATA[
                                        def test_empty_file():
                                            assert False, "CSV processor doesn't handle empty files"
                                        ]]></test_code>
                                    </test>
                                </tests>
                                <test_results>
                                    <result>
                                        <status>failed</status>
                                        <output>Failed: CSV processor doesn't handle empty files</output>
                                        <error>AssertionError: Expected handling of empty files</error>
                                        <timestamp>20240315_123456</timestamp>
                                    </result>
                                </test_results>
                            </test_file>
                        </test_files>
                    </test_suite>
                </generation>
                <dependencies>
                    <dependency>
                        <name>pandas</name>
                        <version>2.0.0</version>
                    </dependency>
                </dependencies>
                <build>
                    <build_script><![CDATA[
                    pip install -r requirements.txt
                    python -m pytest
                    ]]></build_script>
                    <build_status>failed</build_status>
                    <build_logs><![CDATA[
                    Test failed: CSV processor doesn't handle empty files
                    ]]></build_logs>
                </build>
                <package>
                    <package_name>csv_processor</package_name>
                    <package_version>0.1.0</package_version>
                    <package_files>
                        <package_file>src/csv_processor.py</package_file>
                    </package_files>
                    <package_metadata>
                        <license>MIT</license>
                        <repository>https://github.com/test/csv_processor</repository>
                    </package_metadata>
                </package>
            </code_project>
            """
        }

    def test_iteration_phase(self):
        result = self.iterator.run(self.test_state)
        
        # Check if iteration was successful
        self.assertTrue(result["iteration_result"]["success"])
        
        # Verify XML state was updated
        self.assertIsNotNone(result["xml_state"])
        
        # Check if debug file was created
        iteration_file = Path("debug_output") / result["iteration_result"]["iteration_file"]
        self.assertTrue(iteration_file.exists())
        
        # Validate XML content
        self.assertTrue(self.iterator.validate_xml(result["xml_state"]))
        
        # Verify planning section was updated with empty file handling
        self.assertIn("empty files", result["xml_state"].lower())
        
        # Verify all required sections are present
        xml_root = ET.fromstring(result["xml_state"])
        required_sections = ["metadata", "planning", "generation", "dependencies", "build", "package"]
        for section in required_sections:
            self.assertIsNotNone(xml_root.find(section), f"Missing required section: {section}")
        
        # Verify planning section was updated but other sections remained unchanged
        original_root = ET.fromstring(self.test_state["xml_state"])
        for section in required_sections:
            if section != "planning":
                original_section = ET.tostring(original_root.find(section), encoding='unicode')
                updated_section = ET.tostring(xml_root.find(section), encoding='unicode')
                self.assertEqual(original_section, updated_section, f"Section {section} was modified")

    def test_error_handling(self):
        # Test with empty state
        with self.assertRaises(ValueError):
            self.iterator.run({})
        
        # Test with invalid XML
        invalid_state = {"xml_state": "<invalid>XML</invalid>"}
        result = self.iterator.run(invalid_state)
        self.assertFalse(result["iteration_result"]["success"])

if __name__ == '__main__':
    unittest.main()
