import React from 'react';
import StringField from './fields/StringField';
import NumberField from './fields/NumberField';
import BooleanField from './fields/BooleanField';
import ObjectField from './fields/ObjectField';
import ArrayField from './fields/ArrayField';
import OneOfField from './fields/OneOfField';
import { resolveRef } from './utils';

const getFieldComponent = (schema) => {
  if (schema.oneOf || schema.anyOf) {
    return OneOfField; // Using OneOfField to handle both oneOf and anyOf
  }
  if (schema.type === 'object' || schema.properties) {
    return ObjectField;
  }
  if (schema.type === 'array') {
    return ArrayField;
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
  return () => <div>Unsupported field type: {schema.type}</div>;
};

const Field = ({ name, label, schema, rootSchema, value, onChange, errors = [] }) => {
  const resolvedSchema = resolveRef(schema, rootSchema);
  const FieldComponent = getFieldComponent(resolvedSchema);

  return (
    <div style={{ marginBottom: '1rem' }}>
      <label htmlFor={name} style={{ fontWeight: 'bold' }}>{label}</label>
      {schema.description && <p style={{ fontSize: '0.8rem', color: '#666', marginTop: 0 }}>{schema.description}</p>}
      <FieldComponent
        name={name}
        schema={resolvedSchema}
        rootSchema={rootSchema}
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
