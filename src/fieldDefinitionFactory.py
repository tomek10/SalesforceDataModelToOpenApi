from enum import Enum
import re

PICKLIST_VALUE_SEPARATOR = ";"
URL_FIELD_DESCRIPTION = "Should be a valid URL, but this is not required."
URL_FIELD_MAX_LENGTH = 255
SF_ID_FIELD_MAX_LENGTH = 18
PHONE_FIELD_MAX_LENGTH = 40
EMAIL_FIELD_MAX_LENGTH = 80


class FieldType(Enum):
    STRING = "string"
    BOOLEAN = "boolean"
    NUMBER = "number"
    INTEGER = "integer"
    OBJECT = "object"


class FieldFormat(Enum):
    DOUBLE = "double"
    EMAIL = "email"
    DATE = "date"
    DATE_TIME = "date-time"


class FieldDefinition:
    def set_type(self, type):
        self.type = type
        return self

    def set_format(self, format):
        self.format = format
        return self

    def set_max_length(self, maxLength):
        self.maxLength = maxLength
        return self

    def set_description(self, description):
        self.description = description
        return self

    def append_description(self, description):
        if (hasattr(self, "description")):
            self.description += (" " + description)
        else:
            self.set_description(description)

    def set_enum(self, enum):
        self.enum = enum
        return self

    def set_properties(self, properties):
        self.properties = properties
        return self


class NumericFieldWrapper:
    def __init__(self, int_size, decimal_places):
        self.int_size = int_size
        self.decimal_places = decimal_places

    def _is_double(self):
        return self.decimal_places > 0

    def _get_type(self):
        return FieldType.NUMBER.value if self._is_double() else FieldType.INTEGER.value

    def _format_description(self):
        description = f"Max integer length: {self.int_size} chars."
        if (self._is_double()):
            description += f" Max decimal places: {self.decimal_places}."
        return description

    def get_field_definition(self):
        field_definition = FieldDefinition() \
            .set_type(self._get_type()) \
            .set_description(self._format_description())
        if (self._is_double()):
            field_definition.set_format(FieldFormat.DOUBLE.value)
        return field_definition


class PicklistFieldWrapper:
    def __init__(self, raw_format, raw_values):
        self.raw_format = raw_format
        self.raw_values = raw_values

    def _is_multi_select(self):
        return "multi" in self.raw_format

    def _is_open(self):
        return "open" in self.raw_format

    def _get_picklist_type(self):
        return "multi-select picklist" if self._is_multi_select() else "picklist"

    def _get_picklist_restriction(self):
        return "Unrestricted" if self._is_open() else "Restricted" 

    def _get_description(self):
        return f"{self._get_picklist_restriction()} {self._get_picklist_type()}."

    def _has_valid_raw_values(self):
        return isinstance(self.raw_values, str) and len(self.raw_values) > 0

    def _get_picklist_values(self):
        return [x.strip() for x in self.raw_values.split(PICKLIST_VALUE_SEPARATOR)]

    def get_field_definition(self):
        return create_base_text_field() \
            .set_description(self._get_description()) \
            .set_enum(self._get_picklist_values() if self._has_valid_raw_values() else ["Values to be defined"])


class RelationshipFieldWrapper:
    def __init__(self, raw_format):
        self.raw_format = raw_format

    def _extract_relationship_definition(self):
        definition_search = re.search(r"(?<=\().+?(?=\))", self.raw_format)
        search_result = definition_search.group(0)
        if (search_result is None or len(search_result) == 0):
            raise Exception(f'Could not determine relationship field format for "{self.raw_format}"!')

        results = search_result.split(".")
        if (len(results) == 1):
            self.object_api_name = results[0]
            self.is_linked_by_ext_id = False
        elif (len(results) == 2):
            self.object_api_name = results[0]
            self.field_api_name = results[1]
            self.is_linked_by_ext_id = True
        else:
            raise Exception(f'Could not determine relationship field format for "{self.raw_format}"!')

    def get_field_definition(self):
        self._extract_relationship_definition()
        if (self.is_linked_by_ext_id):
            return FieldDefinition() \
                .set_type(FieldType.OBJECT.value) \
                .set_properties({ self.field_api_name: FieldType.STRING.value })
        else:
            return FieldDefinition() \
                .set_type(FieldType.STRING.value) \
                .set_max_length(SF_ID_FIELD_MAX_LENGTH)


def create_base_text_field():
    return FieldDefinition() \
        .set_type(FieldType.STRING.value)


def create_text_field(raw_format):
    field_def = create_base_text_field()
    max_length = get_max_length(raw_format)
    if (max_length is not None):
        field_def.set_max_length(max_length)
    return field_def


def get_max_length(raw_format):
    max_length_search_result = re.search(r"([0-9]+)", raw_format)
    if max_length_search_result is not None:
        return int(max_length_search_result.group(0))
    return None


def create_url_field():
    return create_base_text_field() \
        .set_max_length(URL_FIELD_MAX_LENGTH) \
        .set_description(URL_FIELD_DESCRIPTION)


def create_phone_field():
    return create_base_text_field() \
        .set_max_length(PHONE_FIELD_MAX_LENGTH)


def create_email_field():
    return create_base_text_field() \
        .set_format(FieldFormat.EMAIL.value) \
        .set_max_length(EMAIL_FIELD_MAX_LENGTH)


def create_datetime_field():
    return create_base_text_field() \
        .set_format(FieldFormat.DATE_TIME.value)


def create_date_field():
    return create_base_text_field() \
        .set_format(FieldFormat.DATE.value)


def create_checkbox_field():
    return FieldDefinition() \
        .set_type(FieldType.BOOLEAN.value)


def create_picklist_field(raw_format, raw_values):
    return PicklistFieldWrapper(raw_format, raw_values) \
        .get_field_definition()


def create_numeric_field(raw_format):
    field_sizes = extract_numeric_field_sizes(raw_format)
    return NumericFieldWrapper(field_sizes["int_size"], field_sizes["decimal_places"]) \
        .get_field_definition()


def create_relationship_field(raw_format):
    return RelationshipFieldWrapper(raw_format) \
        .get_field_definition()


def extract_numeric_field_sizes(raw_format):
    sizes_search_result = re.findall(r"([0-9]+)", raw_format)
    if (valid_numeric_field_sizes_found(sizes_search_result)):
        return {
            "int_size": int(sizes_search_result[0]),
            "decimal_places": int(sizes_search_result[1])
        }
    else:
        raise Exception(f'Could not convert to any numeric format: "{raw_format}"!')


def valid_numeric_field_sizes_found(sizes_search_result):
    return sizes_search_result is not None \
        and len(sizes_search_result) == 2