import React, { useImperativeHandle, useRef } from 'react';
import { AutoField, AutoForm, ErrorsField } from 'uniforms-unstyled';
import CollapsibleObjectField from './CollapsibleObjectField';
import { JSONSchemaBridge } from 'uniforms-bridge-json-schema';
import Ajv from 'ajv';
import ajvFormats from 'ajv-formats';
import LlmBotConfigField from './LlmBotConfigField';

const ajv = new Ajv({ allErrors: true, useDefaults: true, strict: false });
ajvFormats(ajv);

function createValidator(schema) {
  const validator = ajv.compile(schema);

  return model => {
    validator(model);
    return validator.errors?.length ? { details: validator.errors } : null;
  };
}

const UniformsForm = React.forwardRef(({ schema, formData, onChange, onSubmit, uiSchema, className, disabled }, ref) => {
  const formRef = useRef();
  const schemaValidator = createValidator(schema);
  const bridge = new JSONSchemaBridge(schema, schemaValidator);

  useImperativeHandle(ref, () => ({
    submit: () => {
      formRef.current.submit();
    }
  }));

  return (
    <AutoForm schema={bridge} model={formData} onChangeModel={onChange} onSubmit={onSubmit} className={className} ref={formRef} disabled={disabled}>
      <AutoField name="general_config" component={CollapsibleObjectField} hiddenFields={['user_id']} />
      <AutoField
        name="llm_bot_config"
        component={LlmBotConfigField}
        uiSchema={uiSchema}
        enumNames={uiSchema.llm_bot_config.llm_provider_config.provider_config.api_key_source['ui:enumNames']}
      />
      <AutoField name="chat_provider_config" component={CollapsibleObjectField} />
      <AutoField name="queue_config" component={CollapsibleObjectField} />
      <ErrorsField />
    </AutoForm>
  );
});

export default UniformsForm;
