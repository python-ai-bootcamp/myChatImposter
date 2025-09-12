import React from 'react';
import StringField from './fields/StringField';
import NumberField from './fields/NumberField';
import BooleanField from './fields/BooleanField';
import ObjectField from './fields/ObjectField';
import ArrayField from './fields/ArrayField';
import OneOfField from './fields/OneOfField'; // New import

const getFieldComponent = (schema) => {
  if (schema.oneOf) {
    return OneOfField;
  }
  if (schema.type === 'string') {
    return StringField;
  }
  if (schema.type === 'number' || schema.type === 'integer') {
    return NumberField;
  }
  if (schema.type === 'boolean') {
    return BooleanField;
  }
  if (schema.type === 'object') {
    return ObjectField;
  }
  if (schema.type === 'array') {
    return ArrayField;
  }
  return () => <div>Unsupported field type: {schema.type}</div>;
};

const Field = ({ name, label, schema, value, onChange, errors = [] }) => {
  const FieldComponent = getFieldComponent(schema);

  return (
    <div style={{ marginBottom: '1rem' }}>
      <label htmlFor={name} style={{ fontWeight: 'bold' }}>{label}</label>
      {schema.description && <p style={{ fontSize: '0.8rem', color: '#666', marginTop: 0 }}>{schema.description}</p>}
      <FieldComponent
        name={name}
        schema={schema}
        value={value}
        onChange={onChange}
        errors={errors}
      />
      {errors.length > 0 && (
        <div style={{ color: 'red', marginTop: '0.5rem' }}>
          {errors.map((error, i) => (
            <div key={i}>{error.message}</div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Field;
