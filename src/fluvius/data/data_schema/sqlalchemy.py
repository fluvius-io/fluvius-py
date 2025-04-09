import sqlalchemy as sa

from fluvius.data.constant import ITEM_ID_FIELD
from sqlalchemy.orm import declarative_base
from fluvius.helper import camel_to_lower


# Create the base class for all models
class SqlaDataSchema(declarative_base()):
    """Base SQLAlchemy Model for automatic serialization and
    deserialization of columns and nested relationships.
    Usage::
        >>> class User(Model):
        >>>     id = db.Column(db.Integer(), primary_key=True)
        >>>     email = db.Column(db.String(), index=True)
        >>>     name = db.Column(db.String())
        >>>     password = db.Column(db.String())
        >>>     posts = db.relationship('Post', backref='user', lazy='dynamic')
        >>>     ...
        >>>     __default_fields__ = ['email', 'name']
        >>>     __hidden_fields__ = ['password']
        >>>     __readonly_fields__ = ['email', 'password']
        >>>
        >>> class Post(Model):
        >>>     id = db.Column(db.Integer(), primary_key=True)
        >>>     user_id = db.Column(db.String(), db.ForeignKey('user.id'), nullable=False)
        >>>     title = db.Column(db.String())
        >>>     ...
        >>>     __default_fields__ = ['title']
        >>>     __readonly_fields__ = ['user_id']
        >>>
        >>> model = User(email='john@localhost')
        >>> db.session.add(model)
        >>> db.session.commit()
        >>>
        >>> # update name and create a new post
        >>> validated_input = {'name': 'John', 'posts': [{'title':'My First Post'}]}
        >>> model.set_columns(**validated_input)
        >>> db.session.commit()
        >>>
        >>> print(model.to_dict(show=['password', 'posts']))
        >>> {u'email': u'john@localhost', u'posts': [{u'id': 1, u'title': u'My First Post'}], u'name': u'John', u'id': 1}
    """
    __abstract__ = True

    @classmethod
    def _resource_from_tablename(cls):
        if not hasattr(cls, '__tablename__'):
            cls.__tablename__ = camel_to_lower(cls.__name__)

        cls.__resource__ = cls.__tablename__
        return cls.__resource__

    @classmethod
    def _register_with_driver(cls, data_driver):
        from fluvius.data.data_driver import DataDriver
        if not (data_driver and issubclass(data_driver, DataDriver)):
            raise ValueError(f'Invalid data driver: {data_driver}')

        resource_name = cls._resource_from_tablename()
        data_driver.register_schema(resource_name)(cls)

    @classmethod
    def _primary_key(cls):
        id_field = getattr(cls, '__primary_key__', ITEM_ID_FIELD)
        return getattr(cls, id_field)


    # Stores changes made to this model's attributes. Can be retrieved
    # with model.changes
    _changes = {}

    def __init__(self, **kwargs):
        super().__init__()
        self._set_columns(_force=True, **kwargs)

    def _set_columns(self, _force=False, **kwargs):
        readonly = getattr(self, '__readonly_fields__', [])
        readonly += getattr(self, '__hidden_fields__', [])
        readonly += [
            ITEM_ID_FIELD,
            '_created',
            '_updated',
            '_creator',
            '_updater',
            '_etag',
        ]

        changes = {}

        columns = self.__table__.columns.keys()
        relationships = self.__mapper__.relationships.keys()

        for key in columns:
            allowed = True if _force or key not in readonly else False
            exists = True if key in kwargs else False
            if allowed and exists:
                val = getattr(self, key)
                if val != kwargs[key]:
                    changes[key] = {'old': val, 'new': kwargs[key]}
                    setattr(self, key, kwargs[key])

        for rel in relationships:
            allowed = True if _force or rel not in readonly else False
            exists = True if rel in kwargs else False
            if allowed and exists:
                is_list = self.__mapper__.relationships[rel].uselist
                if is_list:
                    valid_ids = []
                    query = getattr(self, rel)
                    cls = self.__mapper__.relationships[rel].argument()
                    for item in kwargs[rel]:
                        if 'id' in item and query.filter_by(id=item['id']).limit(1).count() == 1:
                            obj = cls.query.filter_by(id=item['id']).first()
                            col_changes = obj.set_columns(**item)
                            if col_changes:
                                col_changes['id'] = str(item['id'])
                                if rel in changes:
                                    changes[rel].append(col_changes)
                                else:
                                    changes.update({rel: [col_changes]})
                            valid_ids.append(str(item['id']))
                        else:
                            col = cls()
                            col_changes = col.set_columns(**item)
                            query.append(col)
                            db.session.flush()
                            if col_changes:
                                col_changes['id'] = str(col.id)
                                if rel in changes:
                                    changes[rel].append(col_changes)
                                else:
                                    changes.update({rel: [col_changes]})
                            valid_ids.append(str(col.id))

                    # delete related rows that were not in kwargs[rel]
                    for item in query.filter(not_(cls.id.in_(valid_ids))).all():
                        col_changes = {
                            'id': str(item.id),
                            'deleted': True,
                        }
                        if rel in changes:
                            changes[rel].append(col_changes)
                        else:
                            changes.update({rel: [col_changes]})
                        db.session.delete(item)

                else:
                    val = getattr(self, rel)
                    if self.__mapper__.relationships[rel].query_class is not None:
                        if val is not None:
                            col_changes = val.set_columns(**kwargs[rel])
                            if col_changes:
                                changes.update({rel: col_changes})
                    else:
                        if val != kwargs[rel]:
                            setattr(self, rel, kwargs[rel])
                            changes[rel] = {'old': val, 'new': kwargs[rel]}

        return changes

    def _reset_changes(self):
        self._changes = {}

    def create(self):
        pass

    def set(self, **kwargs):
        self._changes = self._set_columns(**kwargs)
        if '_updated' in self.__table__.columns:
            self._updated = datetime.utcnow()

        return self._changes


    def serialize(self, show=None, hide=None, path=None, show_all=True, show_none=False):
        """ Return a dictionary representation of this model.
        """

        show = show or []
        hide = hide or []

        hidden = getattr(self, '__hidden_fields__', [])
        default = getattr(self, '__default_fields__', [])

        ret_data = {}

        if not path:
            path = self.__tablename__.lower()
            def prepend_path(item):
                item = item.lower()
                if item.split('.', 1)[0] == path:
                    return item
                if len(item) == 0:
                    return item
                if item[0] != '.':
                    item = '.%s' % item
                item = '%s%s' % (path, item)
                return item
            show[:] = [prepend_path(x) for x in show]
            hide[:] = [prepend_path(x) for x in hide]

        columns = self.__table__.columns.keys()
        relationships = self.__mapper__.relationships.keys()
        properties = dir(self)

        for key in columns:
            check = '%s.%s' % (path, key)
            if check in hide or key in hidden:
                continue

            if show_all or key == ITEM_ID_FIELD or check in show or key in default:
                val = getattr(self, key)
                if show_none or val is not None:
                    ret_data[key] = val

        for key in relationships:
            check = '%s.%s' % (path, key)
            if check in hide or key in hidden:
                continue
            if show_all or check in show or key in default:
                hide.append(check)
                is_list = self.__mapper__.relationships[key].uselist
                if is_list:
                    ret_data[key] = []
                    for item in getattr(self, key):
                        ret_data[key].append(item.to_dict(
                            show=show,
                            hide=hide,
                            path=('%s.%s' % (path, key.lower())),
                            show_all=show_all,
                        ))
                else:
                    if self.__mapper__.relationships[key].query_class is not None:
                        ret_data[key] = getattr(self, key).to_dict(
                            show=show,
                            hide=hide,
                            path=('%s.%s' % (path, key.lower())),
                            show_all=show_all,
                        )
                    else:
                        ret_data[key] = getattr(self, key)

        for key in list(set(properties) - set(columns) - set(relationships)):
            if key.startswith('_'):
                continue
            check = '%s.%s' % (path, key)
            if check in hide or key in hidden:
                continue

            if show_all or check in show or key in default:
                val = getattr(self, key)
                try:
                    ret_data[key] = json.loads(json.dumps(val))
                except:
                    pass
        return ret_data
