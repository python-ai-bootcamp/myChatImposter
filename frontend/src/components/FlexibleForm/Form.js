import React from 'react';
import Field from './Field';

const FlexibleForm = ({ layout, schema, formData, onFormChange, errors = [], children }) => {
  if (!schema || !formData) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      {layout.sections.map((section) => (
        <div key={section.id} className="form-section" style={{ border: '1px solid #ccc', borderRadius: '4px', padding: '1rem', marginBottom: '1rem' }}>
          <h2>{section.title}</h2>
          {section.fields.map((fieldConfig) => {
            if (fieldConfig.hidden) {
              return null;
            }
            const fieldName = fieldConfig.name;
            const fieldSchema = schema.properties[fieldName];
            if (!fieldSchema) {
              return <div key={fieldName}>Field "{fieldName}" not found in schema</div>;
            }

            // Pass all errors that start with this field's path
            const fieldErrors = errors.filter(e => e.instancePath.startsWith(`/${fieldName}`));

            return (
              <Field
                key={fieldName}
                name={fieldName}
                label={fieldSchema.title || fieldName}
                schema={fieldSchema}
                value={formData[fieldName]}
                onChange={(fieldValue) => {
                  const newFormData = { ...formData, [fieldName]: fieldValue };
                  onFormChange(newFormData);
                }}
                errors={fieldErrors}
              />
            );
          })}
        </div>
      ))}
      {children}
    </div>
  );
};

export default FlexibleForm;
