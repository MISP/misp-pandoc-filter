#!/usr/bin/env python3

import json
import sys


# representation of a JSON event in MISP
class MISPEvent:

    def __init__(self, event_json):
        event_json_file = open(event_json, "r")
        event_json = json.load(event_json_file)
        event_json_file.close()

        response = event_json.get("response", [])
        if len(response) > 0:
            self.event = response[0].get("Event", {})
        else:
            self.event = {}

    def get_objects(self):
        return self.event.get("Object", [])

    def get_attributes(self):
        return self.event.get("Attribute", [])

    def get_tags(self):
        return self.event.get("Tag", [])

    def get_object(self, object_id):
        objects = self.get_objects()
        return next(
            (
                obj for obj in objects 
                if obj.get("uuid") == object_id
            ), 
            None
        )

    def get_attribute(self, attribute_id):
        all_attributes = []
        
        attributes = self.get_attributes()
        all_attributes += attributes
        
        objects = self.get_objects()
        for obj in objects:
            all_attributes += obj["Attribute"]

        return next(
            (
                attr for attr in all_attributes 
                if attr.get("uuid") == attribute_id
            ),
            None
        )

    def get_tag(self, tag_name):
        tags = self.get_tags()
        return next(
            (
                tag for tag in tags 
                if tag.get("name") == tag_name
            ), 
            None
        )

    def get_item_value(self, item_scope, item_identifier):
        value = ""

        if item_scope == "object":
            item = self.get_object(item_identifier)
            if isinstance(item, dict):
                attrs = item.get("Attribute", [])
                if len(attrs) > 0 and isinstance(attrs[0], dict):
                    value = attrs[0].get("value", "")                
        elif item_scope == "attribute":
            item = self.get_attribute(item_identifier)
            if isinstance(item, dict):
                value = item.get("value", "")
        elif item_scope == "tag":
            item = self.get_tag(item_identifier)
            if isinstance(item, dict):
                value = item.get("name", "")

        return value


# steps through the Pandoc JSON AST
# check whether each item is a MISP tag 
# if so, replaces it with the appropriate value
# in inline code block format
class MISPTagParser:

    def __init__(self, ast, ast_generator, misp_event):
        self.ast = ast
        self.ast_generator = ast_generator
        self.misp_event = misp_event

    def find_and_replace(self):
        return self.walk(self.ast)

    def walk(self, data):
        if isinstance(data, list):
            accum = []
            for index in range(len(data)):
                if self.is_valid_misp_tag(data, index):
                    accum.pop()
                    replacement = self.replace_misp_tag(data[index])
                    accum.append(replacement)
                else:
                    accum.append(self.walk(data[index]))
            return accum
        elif isinstance(data, dict):
            accum = {}
            for key, value in data.items():
                accum[key] = self.walk(value)
            return accum
        else:
            return data

    def is_valid_misp_tag(self, data, index):
        misp_tags = ["object", "attribute", "tag"]
        return (
            index > 0 and 
            isinstance(data[index - 1], dict) and 
            data[index - 1].get("t") == "Str" and
            data[index - 1].get("c") == "@" and
            isinstance(data[index], dict) and 
            data[index].get("t") == "Link" and
            isinstance(data[index].get("c"), list) and
            len(data[index].get("c")) >= 3 and
            isinstance(data[index].get("c")[1], list) and
            len(data[index].get("c")[1]) >= 1 and
            isinstance(data[index].get("c")[1][0], dict) and
            data[index].get("c")[1][0].get("t") == "Str" and
            data[index].get("c")[1][0].get("c") in misp_tags and
            isinstance(data[index].get("c")[2], list) and
            len(data[index].get("c")[2]) >= 1
        )

    def replace_misp_tag(self, data):
        content = data.get("c")
        scope = content[1][0].get("c")
        identifier = content[2][0]

        value = self.misp_event.get_item_value(scope, identifier)
        codeblock = self.ast_generator.generate_inline_codeblock(value)

        return codeblock


# add an appendix to the pandoc AST 
# which includes all the objects and attributes 
# found in the MISP event
class AppendixGenerator:
    
    def __init__(self, ast_generator, misp_event):
        self.ast_generator = ast_generator
        self.misp_event = misp_event

    def generate_appendix(self):
        appendix = []

        pagebreak = self.ast_generator.generate_latex("\\pagebreak")
        appendix.append(pagebreak)

        header = self.ast_generator.generate_header(1, "Appendix")
        appendix.append(header)

        table_data = self.generate_table_data()
        for (index, data) in enumerate(table_data):
            header_text = "Attributes" if index == 0 else "Object " + str(index)
            header = self.ast_generator.generate_header(3, header_text)
            table = self.ast_generator.generate_table(data)
            appendix.append(header)
            appendix.append(table)

        return appendix

    def generate_table_data(self):
        tables = []
        headers = ["Category", "Type", "Value"]

        attributes = self.misp_event.get_attributes()
        table_data = { "headers": headers, "rows": [] }
        for attr in attributes:
            table_data.get("rows", []).append([
                attr.get("category", ""), 
                attr.get("type", ""), 
                attr.get("value", "")
            ])
        tables.append(table_data)
        
        objects = self.misp_event.get_objects()
        for obj in objects:
            table_data = { "headers": headers,"rows": [] }
            for attr in obj.get("Attribute", []):
                table_data.get("rows", []).append([
                    attr.get("category", ""), 
                    attr.get("type", ""), 
                    attr.get("value", "")
                ])
            tables.append(table_data)

        return tables
        

# generates various items in AST format
class ASTGenerator:

    def generate_header(self, level, content):
        header = {
            "t": "Header",
            "c": [
                1,
                ["heading-level-" + str(level), [], []],
                []
            ]
        }

        words = content.split(" ")
        for (index, word) in enumerate(words):
            header["c"][2].append({ "t": "Str", "c": word })
            if (index) <= len(words) - 1:
                header["c"][2].append({ "t": "Space" })

        return header

    def generate_inline_codeblock(self, content):
        codeblock = { 
            "t": "Code", 
            "c": [["", [], []], content] 
        }

        return codeblock

    def generate_latex(self, command):
        latex = { 
            "t": "RawBlock", 
            "c": ["tex", command] 
        }

        return latex

    def generate_table(self, table_data):
        table = { 
            "t": "Table", 
            "c": [["", [], []], [None, []], [], [], [], [["", [], []], []]]
        }

        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])

        for h in headers:
            table["c"][2].append([{ "t": "AlignDefault" }, { "t": "ColWidthDefault" }])

        table["c"][3] = self.generate_table_header(headers)
        table["c"][4] = self.generate_table_body(rows)

        return table

    def generate_table_header(self, header_data):
        header = [["", [], []], []]
        header[1].append(self.generate_table_row(header_data))

        return header

    def generate_table_body(self, body_data):
        body = [[["", [], []], 0, [], []]]
        for row in body_data:
            body[0][3].append(self.generate_table_row(row))

        return body

    def generate_table_row(self, row_data):
        row = [["", [], []], []]
        for cell in row_data:
            row[1].append(self.generate_table_cell(cell))

        return row

    def generate_table_cell(self, cell_data):
        cell = [
            ["", [], []],
            { "t": "AlignDefault" }, 
            1, 
            1,
            [{ 
                "t": "Plain", 
                "c": [{ "t": "Str", "c": cell_data }] 
            }]
        ]

        return cell


# load the AST from stdin
# process it
# return the modified AST to stdout
def main():
    ast = json.load(sys.stdin)

    ast_generator = ASTGenerator()
    misp_event = MISPEvent("event.json")
    misp_tag_parser = MISPTagParser(ast, ast_generator, misp_event)
    appendix_generator = AppendixGenerator(ast_generator, misp_event) 

    ast = misp_tag_parser.find_and_replace()
    appendix = appendix_generator.generate_appendix()
    ast["blocks"] += appendix

    json.dump(ast, sys.stdout)


if __name__ == "__main__":
    main()

