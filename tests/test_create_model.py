import pytest

from pydantic import BaseModel, ValidationError, create_model, errors, validator


def test_create_model():
    model = create_model('FooModel', foo=(str, ...), bar=123)
    assert issubclass(model, BaseModel)
    assert issubclass(model.__config__, BaseModel.Config)
    assert model.__name__ == 'FooModel'
    assert model.__fields__.keys() == {'foo', 'bar'}
    assert model.__validators__ == {}
    assert model.__config__.__name__ == 'Config'


def test_create_model_usage():
    model = create_model('FooModel', foo=(str, ...), bar=123)
    m = model(foo='hello')
    assert m.foo == 'hello'
    assert m.bar == 123
    with pytest.raises(ValidationError):
        model()
    with pytest.raises(ValidationError):
        model(foo='hello', bar='xxx')


def test_invalid_name():
    with pytest.warns(RuntimeWarning):
        model = create_model('FooModel', _foo=(str, ...))
    assert len(model.__fields__) == 0


def test_field_wrong_tuple():
    with pytest.raises(errors.ConfigError):
        create_model('FooModel', foo=(1, 2, 3))


def test_config_and_base():
    with pytest.raises(errors.ConfigError):
        create_model('FooModel', __config__=BaseModel.Config, __base__=BaseModel)


def test_inheritance():
    class BarModel(BaseModel):
        x = 1
        y = 2
    model = create_model('FooModel', foo=(str, ...), bar=(int, 123), __base__=BarModel)
    assert model.__fields__.keys() == {'foo', 'bar', 'x', 'y'}
    m = model(foo='a', x=4)
    assert m.dict() == {'bar': 123, 'foo': 'a', 'x': 4, 'y': 2}


def test_custom_config():
    class Config(BaseModel.Config):
        fields = {
            'foo': 'api-foo-field'
        }
    model = create_model('FooModel', foo=(int, ...), __config__=Config)
    assert model(**{'api-foo-field': '987'}).foo == 987
    with pytest.raises(ValidationError):
        model(foo=654)


def test_inheritance_validators():
    class BarModel(BaseModel):
        @validator('a', check_fields=False)
        def check_a(cls, v):
            if 'foobar' not in v:
                raise ValueError('"foobar" not found in a')
            return v

    model = create_model('FooModel', a='cake', __base__=BarModel)
    assert model().a == 'cake'
    with pytest.raises(ValidationError):
        model(a='something else')


def test_inheritance_validators_all():
    class BarModel(BaseModel):
        @validator('*')
        def check_all(cls, v):
            return v * 2

    model = create_model('FooModel', a=(int, ...), b=(int, ...), __base__=BarModel)
    assert model(a=2, b=6).dict() == {'a': 4, 'b': 12}


def test_funky_name():
    model = create_model('FooModel', **{'this-is-funky': (int, ...)})
    m = model(**{'this-is-funky': '123'})
    assert m.dict() == {'this-is-funky': 123}
    with pytest.raises(ValidationError) as exc_info:
        model()
    assert exc_info.value.flatten_errors() == [
        {
            'loc': ('this-is-funky',),
            'msg': 'field required',
            'type': 'value_error.missing',
        },
    ]


def test_repeat_base_usage():
    class Model(BaseModel):
        a: str

    assert Model.__fields__.keys() == {'a'}

    model = create_model('FooModel', b=1, __base__=Model)

    assert Model.__fields__.keys() == {'a'}
    assert model.__fields__.keys() == {'a', 'b'}

    model2 = create_model('Foo2Model', c=1, __base__=Model)

    assert Model.__fields__.keys() == {'a'}
    assert model.__fields__.keys() == {'a', 'b'}
    assert model2.__fields__.keys() == {'a', 'c'}

    model3 = create_model('Foo2Model', d=1, __base__=model)

    assert Model.__fields__.keys() == {'a'}
    assert model.__fields__.keys() == {'a', 'b'}
    assert model2.__fields__.keys() == {'a', 'c'}
    assert model3.__fields__.keys() == {'a', 'b', 'd'}
