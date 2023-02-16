#!/usr/bin/python3 -i
#
# Copyright 2020-2023 The Khronos Group Inc.
#
# SPDX-License-Identifier: Apache-2.0

# Description:
# -----------
# This script validates a json pipeline file against the schema files.

import os,sys
import re
import argparse
import json
import jsonschema

base_schema_filename = os.path.join("..", "json", "vk.json")
vkpcc_schema_filename = os.path.join("..", "json", "vkpcc.json")

# Parses input arguments
def ParseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('json_file', help='The json file to validate')
    return parser.parse_args()

def main():
    args           = ParseArgs()
    jsonText       = ""
    baseSchemaText = ""
    vkSchemaText   = ""

    # Exit with error if json or schema files do not exist
    if not os.path.exists(args.json_file):
        print('Error: json file \"%s\" does not exist.' % args.json_file)
        sys.exit(1)
    elif not os.path.exists(base_schema_filename):
        print('Error: json file \"%s\" does not exist.' % base_schema_filename)
        sys.exit(1)
    elif not os.path.exists(vkpcc_schema_filename):
        print('Error: json file \"%s\" does not exist.' % vkpcc_schema_filename)
        sys.exit(1)

    # Read the json schemas files in as text
    with open(base_schema_filename) as baseSchemaFile:
        baseSchemaText = baseSchemaFile.read()
    with open(vkpcc_schema_filename) as vkSchemaFile:
        vkSchemaText = vkSchemaFile.read()
    with open(args.json_file) as jsonFile:
        jsonText = jsonFile.read()
    baseSchema = json.loads(baseSchemaText)
    vkSchema   = json.loads(vkSchemaText)
    jsonData   = json.loads(jsonText)

    # Ensure that the generated vk.json schema is a valid schema
    try:
        jsonschema.Draft4Validator.check_schema(baseSchema)
        print(base_schema_filename, "is valid")
    except jsonschema.SchemaError as e:
        print(base_schema_filename, "error: " + str(e))

    # Ensure that vkpcc.json is also a valid schema
    try:
        jsonschema.Draft4Validator.check_schema(vkSchema)
        print(vkpcc_schema_filename, "schema is valid")
    except jsonschema.exceptions.SchemaError as e:
        print(vkpcc_schema_filename, "schema error: " + str(e))

    # Construct a schema validator object from the two schema files
    schemaRefStore = {
        baseSchema["id"] : baseSchema,
        vkSchema["id"]   : vkSchema
    }
    resolver  = jsonschema.RefResolver.from_schema(baseSchema, store=schemaRefStore)
    validator = jsonschema.Draft4Validator(vkSchema, resolver=resolver)

    # Validate the input .json file using the schemas
    for error in sorted(validator.iter_errors(jsonData), key=str):
        print(error.message)
        print(list(error.path))
        for suberror in sorted(error.context, key=lambda e: e.schema_path):
            print(list(suberror.path), suberror.message, sep="\n")
        print("\n")

if __name__ == '__main__':
    main()
