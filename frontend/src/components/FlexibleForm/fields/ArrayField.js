import React from 'react';
import Field from '../Field';

const ArrayField = ({ name, schema, rootSchema, value, onChange, errors = [] }) => {
  const arrayValue = Array.isArray(value) ? value : [];

  const handleItemChange = (index, itemValue) => {
    const newValue = [...arrayValue];
    newValue[index] = itemValue;
    onChange(newValue);
  };

  const handleAddItem = () => {
    const defaultValue = schema.items.default !== undefined ? schema.items.default : '';
    const newValue = [...arrayValue, defaultValue];
    onChange(newValue);
  };

  const handleRemoveItem = (index) => {
    const newValue = arrayValue.filter((_, i) => i !== index);
    onChange(newValue);
  };

  return (
    <div style={{ border: '1px solid #e0e0e0', padding: '1rem', marginTop: '0.5rem', borderRadius: '4px' }}>
      {arrayValue.map((item, index) => (
        <div key={index} style={{ display: 'flex', alignItems: 'baseline', marginBottom: '0.5rem' }}>
          <div style={{ flex: 1, marginRight: '1rem' }}>
            <Field
              name={`${name}-${index}`}
              label={`Item ${index + 1}`}
              schema={schema.items}
              rootSchema={rootSchema}
              value={item}
              onChange={(itemValue) => handleItemChange(index, itemValue)}
              errors={errors.filter(e => e.instancePath === `/${name}/${index}`)}
            />
          </div>
          <button type="button" onClick={() => handleRemoveItem(index)} style={{ padding: '0.2rem 0.5rem' }}>
            Remove
          </button>
        </div>
      ))}
      <button type="button" onClick={handleAddItem} style={{ marginTop: '0.5rem', padding: '0.3rem 0.6rem' }}>
        Add Item
      </button>
    </div>
  );
};

export default ArrayField;
