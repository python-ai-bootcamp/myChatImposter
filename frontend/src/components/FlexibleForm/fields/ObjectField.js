import React from 'react';
import Field from '../Field';

const ObjectField = ({ name, schema, value, onChange, errors = [] }) => {
  const objectValue = value && typeof value === 'object' ? value : {};

  // Errors for the object itself (e.g. "must be object")
  const selfErrors = errors.filter(e => e.instancePath === `/${name}`);

  return (
    <div style={{ border: '1px solid #e0e0e0', padding: '1rem', marginTop: '0.5rem', borderRadius: '4px' }}>
      {selfErrors.length > 0 && (
        <div style={{ color: 'red', marginBottom: '1rem' }}>
          {selfErrors.map((error, i) => (
            <div key={i}>{error.message}</div>
          ))}
        </div>
      )}
      {Object.keys(schema.properties).map((propertyName) => {
        const propertySchema = schema.properties[propertyName];

        if (propertySchema.ui && propertySchema.ui.hidden) {
          return null;
        }

        // Find errors for this specific property
        const propertyPath = `/${name}/${propertyName}`;
        const propertyErrors = errors.filter(e => e.instancePath === propertyPath);

        // Also find "required" errors that point to this property
        const requiredError = errors.find(e => e.keyword === 'required' && e.params.missingProperty === propertyName);
        if (requiredError) {
            // Add a synthetic error object for the property
            propertyErrors.push({ message: 'is required' });
        }


        return (
          <Field
            key={propertyName}
            name={`${name}-${propertyName}`}
            label={propertySchema.title || propertyName}
            schema={propertySchema}
            value={objectValue[propertyName]}
            onChange={(propertyValue) => {
              const newValue = { ...objectValue, [propertyName]: propertyValue };
              onChange(newValue);
            }}
            errors={propertyErrors}
          />
        );
      })}
    </div>
  );
};

export default ObjectField;
