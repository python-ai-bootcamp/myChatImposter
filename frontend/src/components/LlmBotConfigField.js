import React from 'react';
import { connectField } from 'uniforms';
import { AutoField } from 'uniforms-unstyled';
import CustomSelectField from './CustomSelectField';

const LlmBotConfig = ({ field, enumNames }) => {
  const fields = field.fields;

  return (
    <div>
      {fields.map(fieldName => {
        if (fieldName === 'llm_provider_config') {
          return (
            <AutoField
              key={fieldName}
              name={fieldName}
              component={ProviderConfig}
              enumNames={enumNames}
            />
          );
        }
        return <AutoField key={fieldName} name={fieldName} />;
      })}
    </div>
  );
};

const ProviderConfig = connectField(({ field, enumNames }) => {
  const fields = field.fields;
  return (
    <div>
      {fields.map(fieldName => {
        if (fieldName === 'api_key_source') {
          return (
            <AutoField
              key={fieldName}
              name={fieldName}
              component={CustomSelectField}
              enumNames={enumNames}
            />
          );
        }
        return <AutoField key={fieldName} name={fieldName} />;
      })}
    </div>
  );
});


export default connectField(LlmBotConfig);
