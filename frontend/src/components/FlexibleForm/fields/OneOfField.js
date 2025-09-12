import React from 'react';
import Field from '../Field';

const OneOfField = ({ name, schema, rootSchema, value, onChange, errors = [] }) => {
  const discriminator = 'provider_name';

  const selectedOption = schema.oneOf.find(option => {
    return value && option.properties[discriminator]?.const === value[discriminator];
  });

  const handleSelectionChange = (e) => {
    const selectedTitle = e.target.value;
    const newSelectedOption = schema.oneOf.find(option => option.title === selectedTitle);

    if (newSelectedOption) {
      const newData = {};
      Object.keys(newSelectedOption.properties).forEach(key => {
        const propSchema = newSelectedOption.properties[key];
        if (propSchema.const) {
          newData[key] = propSchema.const;
        } else if (propSchema.default !== undefined) {
          newData[key] = propSchema.default;
        } else {
          newData[key] = undefined;
        }
      });
      onChange(newData);
    }
  };

  return (
    <div style={{ border: '1px solid #e0e0e0', padding: '1rem', marginTop: '0.5rem', borderRadius: '4px' }}>
      <select
        value={selectedOption ? selectedOption.title : ''}
        onChange={handleSelectionChange}
        style={{ marginBottom: '1rem', width: '100%', padding: '0.5rem' }}
      >
        <option value="" disabled>Select an option</option>
        {schema.oneOf.map((option, i) => (
          <option key={i} value={option.title}>{option.title}</option>
        ))}
      </select>

      {selectedOption && (
        <Field
          name={name}
          label=""
          schema={selectedOption}
          rootSchema={rootSchema}
          value={value}
          onChange={onChange}
          errors={errors}
        />
      )}
    </div>
  );
};

export default OneOfField;
