import React from 'react';
import StringField from './fields/StringField';
import NumberField from './fields/NumberField';
import BooleanField from './fields/BooleanField';
import ObjectField from './fields/ObjectField';
import ArrayField from './fields/ArrayField';
import OneOfField from './fields/OneOfField';
import { resolveRef } from './utils';

const getFieldComponent = (schema) => {
  if (schema.oneOf) {
    return OneOfField;
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
      <details>
        <summary style={{ fontWeight: 'bold' }}>{label} (Click to see schema)</summary>
        <pre style={{ backgroundColor: '#eee', padding: '0.5rem', fontSize: '0.7rem' }}>
          <strong>Original Schema:</strong><br />
          {JSON.stringify(schema, null, 2)}
        </pre>
        <pre style={{ backgroundColor: '#eef', padding: '0.5rem', fontSize: '0.7rem' }}>
          <strong>Resolved Schema:</strong><br />
          {JSON.stringify(resolvedSchema, null, 2)}
        </pre>
      </details>

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
