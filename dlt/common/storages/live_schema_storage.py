from typing import Any, Dict, overload

from dlt.common.typing import ConfigValue
from dlt.common.schema.schema import Schema
from dlt.common.storages.schema_storage import SchemaStorage
from dlt.common.configuration.specs import SchemaVolumeConfiguration


class LiveSchemaStorage(SchemaStorage):

    @overload
    def __init__(self, config: SchemaVolumeConfiguration, makedirs: bool = False) -> None:
        ...

    @overload
    def __init__(self, config: SchemaVolumeConfiguration = ConfigValue, makedirs: bool = False) -> None:
        ...

    def __init__(self, config: SchemaVolumeConfiguration = None, makedirs: bool = False) -> None:
        self.live_schemas: Dict[str, Schema] = {}
        super().__init__(config, makedirs)

    def __getitem__(self, name: str) -> Schema:
        # disconnect live schema
        # self.live_schemas.pop(name, None)
        if name in self.live_schemas:
            schema = self.live_schemas[name]
        else:
            # return new schema instance
            schema = super().load_schema(name)
            self._update_live_schema(schema, True)

        return schema

    def load_schema(self, name: str) -> Schema:
        self.commit_live_schema(name)
        # now live schema is saved so we can load it
        return super().load_schema(name)

    def save_schema(self, schema: Schema) -> str:
        rv = super().save_schema(schema)
        # -- update the live schema with schema being saved but do not create live instance if not already present
        # no, cre
        self._update_live_schema(schema, True)
        return rv

    def initialize_import_schema(self, schema: Schema) -> None:
        if self.config.import_schema_path:
            try:
                self._load_import_schema(schema.name)
            except FileNotFoundError:
                # save import schema only if it not exist
                self._export_schema(schema, self.config.import_schema_path)


    def commit_live_schema(self, name: str) -> Schema:
        # if live schema exists and is modified then it must be used as an import schema
        live_schema = self.live_schemas.get(name)
        if live_schema and live_schema.stored_version_hash != live_schema.version_hash:
            live_schema.bump_version()
            # if self.config.import_schema_path:
            #     print("WRITE IMPORT SCHEMA")
            #     raise NotImplementedError()
            #     # overwrite import schemas if specified
            #     self._export_schema(live_schema, self.config.import_schema_path)
            # else:
            # write directly to schema storage if no import schema folder configured
            self._save_schema(live_schema)
        return live_schema

    def _update_live_schema(self, schema: Schema, can_create_new: bool) -> None:
        if schema.name in self.live_schemas:
            # replace content without replacing instance
            self.live_schemas[schema.name].from_dict(schema.to_dict())  # type: ignore
        elif can_create_new:
            self.live_schemas[schema.name] = schema
