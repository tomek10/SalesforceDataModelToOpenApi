import yaml
import pandas as pd
from fieldDefinitionFactory import \
    create_picklist_field, create_text_field, create_url_field, create_phone_field, \
    create_checkbox_field, create_numeric_field, create_email_field, \
    create_datetime_field, create_date_field, create_relationship_field, FieldType

pd.options.mode.chained_assignment = None  # default='warn'

# Original source file column headers
FIELD_FORMAT = "Field Format"
FIELD_API_NAME = "Field Api Name"
PICKLSIT_API_NAMES = "Picklist API Names"
IS_REQUIRED = "Is Required?"
IS_INCLUDED_IN_OPENAPI = "Include in OpenAPI?"
DESCRIPTION = "OpenApi Description"

# Santander source file column headers
# FIELD_FORMAT = "Field Type"
# FIELD_API_NAME = "Field Name"
# PICKLSIT_API_NAMES = "Picklist API names"
# IS_REQUIRED = "Is Required?"
# IS_INCLUDED_IN_OPENAPI = "Include in OpenAPI?"
# DESCRIPTION = "OpenAPI Description"

# Other constants
CUSTOM_API_NAME_SUFFIX = "__c"
CUSTOM_API_RELATIONSHIP_SUFFIX = "__r"
STANDARS_API_NAME_SUFFIX = "Id"


def clean_frame(df):
    df = df.dropna(subset=[FIELD_API_NAME, IS_REQUIRED, IS_INCLUDED_IN_OPENAPI])
    df[IS_REQUIRED] = df[IS_REQUIRED].apply(bool)
    df[IS_INCLUDED_IN_OPENAPI] = df[IS_INCLUDED_IN_OPENAPI].apply(bool)
    df = df[df[IS_INCLUDED_IN_OPENAPI]]
    return df


def get_field_definition(row):
    raw_format = row[FIELD_FORMAT].lower()
    if ("text" in raw_format):
        return create_text_field(raw_format)
    elif ("url" in raw_format):
        return create_url_field()
    elif ("phone" in raw_format):
        return create_phone_field()
    elif("checkbox" in raw_format):
        return create_checkbox_field()
    elif("email" in raw_format):
        return create_email_field()
    elif("date" in raw_format):
        return create_datetime_field() if ("time" in raw_format) else create_date_field()
    elif("picklist" in raw_format):
        return create_picklist_field(raw_format, raw_values=row[PICKLSIT_API_NAMES])
    elif("lookup" in raw_format or "master" in raw_format):
        return create_relationship_field(row[FIELD_FORMAT])
    elif(is_numeric_field(raw_format)):
        return create_numeric_field(raw_format)

    raise Exception(f'Could not determine the field format for api name: "{row[FIELD_API_NAME]}". Format is "{row[FIELD_FORMAT]}".')


def is_numeric_field(raw_format):
    return "number" in raw_format \
        or "percent" in raw_format \
        or "currency" in raw_format


def field_props_valid(props):
    return props is not None and len(props) > 0


def get_yaml_field_api_name(field_definition, field_api_name):
    if(field_definition.type == FieldType.OBJECT.value):
        return convert_to_relationship_name(field_api_name)
    return field_api_name

def convert_to_relationship_name(field_api_name):
    if (field_api_name.endswith(CUSTOM_API_NAME_SUFFIX)):
        return field_api_name.replace(CUSTOM_API_NAME_SUFFIX, CUSTOM_API_RELATIONSHIP_SUFFIX)
    if (field_api_name.endswith(STANDARS_API_NAME_SUFFIX)):
        return field_api_name[:len(field_api_name) - 2]
    return field_api_name


def has_custom_description(row):
    return isinstance(row[DESCRIPTION], str) and len(row[DESCRIPTION]) > 0


def main():
    object_api_names = [
        "Account",
        "AdditionalProduct__c",
        "Asset",
        "Case",
        "Contact",
        "Contract",
        "Quote__c"
    ]
    objects_dict = {}

    for object_api_name in object_api_names:
        df = pd.read_excel('./src/model.xlsx', object_api_name)
        df = clean_frame(df)
        
        all_object_fields = {}
        required_field_api_names = []
        for idx, row in df.iterrows():
            field_definition = get_field_definition(row)
            if (has_custom_description(row)):
                field_definition.append_description(row[DESCRIPTION])
            field_api_name = get_yaml_field_api_name(field_definition, row[FIELD_API_NAME].strip())
            field_props = vars(field_definition)
            if (field_props_valid(field_props)):
                all_object_fields[field_api_name] = field_props
                if (row[IS_REQUIRED]):
                    required_field_api_names.append(field_api_name)

        object_dict = {
            "type": "object",
            "properties": all_object_fields
        }
        if len(required_field_api_names) > 0:
            object_dict["required"] = required_field_api_names

        objects_dict[object_api_name] = object_dict

        with open("model.yaml", "w") as target_file:
            yaml.safe_dump({
                "components": {
                    "schemas": objects_dict
                }
            },
            target_file, sort_keys=False)


main()