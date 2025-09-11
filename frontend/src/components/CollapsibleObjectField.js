import React, { useState } from 'react';
import { connectField, AutoField } from 'uniforms-unstyled';

const Collapsible = ({ label, hiddenFields = [], field }) => {
  const [isOpen, setIsOpen] = useState(false);
  const fields = field.fields;

  return (
    <div style={{ border: '1px solid #ccc', borderRadius: '4px', padding: '1rem', marginBottom: '1rem' }}>
      <button type="button" onClick={() => setIsOpen(!isOpen)} style={{ all: 'unset', cursor: 'pointer', fontWeight: 'bold', fontSize: '1.2rem', display: 'block', width: '100%' }}>
        {isOpen ? '▼' : '►'} {label}
      </button>
      {isOpen && (
        <div style={{ marginTop: '1rem' }}>
          {fields.map(fieldName => {
            if (hiddenFields.includes(fieldName)) {
              return <AutoField key={fieldName} name={fieldName} hidden />;
            }
            return <AutoField key={fieldName} name={fieldName} />;
          })}
        </div>
      )}
    </div>
  );
};

export default connectField(Collapsible);
