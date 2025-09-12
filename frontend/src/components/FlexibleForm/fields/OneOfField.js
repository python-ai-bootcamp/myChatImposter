import React from 'react';
import Field from '../Field';
import { resolveRef } from '../utils';

const OneOfField = ({ name, schema, rootSchema, value, onChange, errors = [] }) => {
  const options = schema.oneOf || schema.anyOf;

  const getSelectedOption = (currentValue) => {
    if (currentValue === null) {
      return options.find(o => o.type === 'null');
    }
    if (typeof currentValue === 'object' && currentValue !== null) {
      // In an anyOf with [schema, null], the non-null option is the one we want for an object value.
      return options.find(o => o.type !== 'null');
    }
    return undefined;
  };

  const handleSelectionChange = (e) => {
    const selectedTitle = e.target.value;
    const newSelectedOption = options.find(option => {
        const resolved = resolveRef(option, rootSchema) || option;
        return resolved.title === selectedTitle;
    });

    if (newSelectedOption) {
      if (newSelectedOption.type === 'null') {
        onChange(null);
        return;
      }

      const resolvedOption = resolveRef(newSelectedOption, rootSchema);
      // If the resolved option has a oneOf, we need to pick the first one as a default
      if (resolvedOption.oneOf && resolvedOption.oneOf.length > 0) {
          const firstChoice = resolveRef(resolvedOption.oneOf[0], rootSchema);
          const newData = {};
           if (firstChoice.properties) {
                Object.keys(firstChoice.properties).forEach(key => {
                    const propSchema = firstChoice.properties[key];
                    if (propSchema.const) {
                        newData[key] = propSchema.const;
                    } else {
                        newData[key] = propSchema.default;
                    }
                });
            }
            onChange(newData);
      } else {
          // This case might need more robust default value generation
          onChange({});
      }
    }
  };

  const selectedOption = getSelectedOption(value);
  const resolvedSelectedOption = resolveRef(selectedOption, rootSchema);
  const selectedTitle = resolvedSelectedOption ? resolvedSelectedOption.title : '';

  return (
    <div style={{ border: '1px solid #e0e0e0', padding: '1rem', marginTop: '0.5rem', borderRadius: '4px' }}>
      <select
        value={selectedTitle}
        onChange={handleSelectionChange}
        style={{ marginBottom: '1rem', width: '100%', padding: '0.5rem' }}
      >
        <option value="" disabled>Select an option</option>
        {options.map((option, i) => {
            const resolved = resolveRef(option, rootSchema) || option;
            return <option key={i} value={resolved.title}>{resolved.title}</option>
        })}
      </select>

      {selectedOption && value !== null && (
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
