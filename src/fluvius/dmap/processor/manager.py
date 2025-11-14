from pyrsistent import PClass, field
from fluvius.dmap.interface import InputAlreadyProcessedError, InputFile
from fluvius.dmap import logger, config

from sqlalchemy import text, create_engine

DEBUG = config.DEBUG_MANAGER


class DataProcessEntry(PClass):
    _id = field()
    file_name = field()
    mime_type = field()
    file_size = field()  # file_resource, process_name, process_signature is unique together
    checksum_sha256 = field()  # file_resource, process_name, process_signature is unique together

    process_name = field()

    status = field()
    status_message = field()
    data_provider = field()
    data_variant = field()
    start_time = field()
    finish_time = field()
    last_updated = field()

    _process_manager = field(mandatory=True, serializer=lambda v, o: None)

    def update(self, **kwargs):
        self._process_manager.update_entry(self, **kwargs)

    def delete(self):
        self._process_manager.delete_entry(self)

    def set_status(self, status, message=None):
        if self.status == status:
            return self

        self._process_manager.update_entry(self, status=status, status_message=message)
        return self.set(status=status)

    def serialize(self):
        data = super(DataProcessEntry, self).serialize()
        data.pop('_process_manager')
        return data


class DataProcessManager(object):
    ''' A manager object for tracking processes that related to a file resource. E.g.
        - Import a file into the database
        - Run a transformation on a file
        - Other ETL tasks, etc.
    '''

    __abstract__ = True
    __registry__ = {}

    def __init_subclass__(cls, **kwargs):
        if cls.__dict__.get('__abstract__'):
            return

        if cls.name in cls.__registry__:
            raise ValueError(f"DataProcessManager [{cls.name}] is already registered!")

        cls.__registry__[cls.name] = cls

    @classmethod
    def init_manager(cls, name, **kwargs):
        if name not in cls.__registry__:
            raise ValueError(f"DataProcessManager [{name}] is not registered!")

        return cls.__registry__[name](**kwargs)

    def register_file(
        self,
        file_resource: InputFile,
        process_name,
        process_signature,
        **kwargs
    ) -> DataProcessEntry:
        ''' check if the file resource has already exists in the process lists, if it is exists, return the entry
        otherwise, create a new one. '''
        raise NotImplementedError

    def update_entry(self, process_entry: DataProcessEntry, **kwargs):
        raise NotImplementedError

    def delete_entry(self, process_entry: DataProcessEntry):
        raise NotImplementedError


class PostgresFileProcessManager(DataProcessManager):
    name = 'postgres'

    def __init__(self, config):
        pt = config.process_tracker
        table = pt['table']
        schema = pt['schema']

        self.process_name = config.process_name
        self.table_addr = f'"{schema}"."{table}"' if schema else f'"{table}"'
        self.uri = pt['uri']
        self.engine = create_engine(self.uri)

    def run_query(self, query_stmt, **kwargs):
        DEBUG and logger.info("\n\tSQL : %s\n\tDATA: %s", query_stmt, str(kwargs))
        with self.engine.connect() as conn:
            result = conn.execute(query_stmt, kwargs)
            conn.commit()

        return result

    def fetch_entry(self, checksum_sha256, process_name=None):
        process_name = process_name or self.process_name
        sql_query = text(
            f'SELECT * from {self.table_addr} WHERE '
            '"checksum_sha256" = :checksum_sha256 AND '
            '"process_name" = :process_name'
        )

        try:
            row = self.run_query(
                sql_query,
                checksum_sha256=checksum_sha256,
                process_name=self.process_name
            ).mappings().one()
        
            return self._construct_entry(row)
        except Exception as e:
            logger.info(f"Not Found Entry: {str(e)}")
            return None

    def _construct_entry(self, data):
        return DataProcessEntry.create({
            '_process_manager': self,
            **data
        }, ignore_extra=True)

    def register_file(
        self,
        file_resource: InputFile,
        process_name=None,
        status=None,
        forced=False,
        **kwargs
    ) -> DataProcessEntry:
        process_name = process_name or self.process_name
        entry = self.fetch_entry(file_resource.sha256sum, process_name)

        if entry is not None:
            if entry.status == 'SUCCESS' and not forced:
                raise InputAlreadyProcessedError

            self.update_entry(entry, status=status, status_message=None, **kwargs)
        else:
            if status is None:
                status = 'UNKNOWN'

            process_entry = self._construct_entry({
                'checksum_sha256': file_resource.sha256sum,
                'process_name': self.process_name,
                'file_name': file_resource.filename,
                'file_size': file_resource.filesize,
                'mime_type': file_resource.filetype,
                'status': status,
                **kwargs
            })

            self._submit_entry(process_entry)
        return self.fetch_entry(file_resource.sha256sum)

    def _submit_entry(self, process_entry):
        data = process_entry.serialize()
        columns = list(data.keys())
        fields_stmt = ', '.join(columns)
        values_stmt = ', '.join([f':{key}' for key in columns])

        query = text(f'INSERT INTO {self.table_addr} ({fields_stmt}) VALUES ({values_stmt})')
        return self.run_query(query, **data)

    def update_entry(self, process_entry, **kwargs):
        set_stmt = ', '.join([f'"{key}" = :{key}' for key in kwargs.keys()])
        query = text(
            f'UPDATE {self.table_addr} SET '
            f'  {set_stmt}, '
            f'  "last_updated" = CURRENT_TIMESTAMP '
            f'WHERE '
            f'   checksum_sha256 = :checksum_sha256 AND '
            f'   process_name = :process_name'
        )

        return self.run_query(
            query,
            checksum_sha256=process_entry.checksum_sha256,
            process_name=process_entry.process_name,
            **kwargs
        )
