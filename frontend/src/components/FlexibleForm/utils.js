export const resolveRef = (schema, rootSchema) => {
  if (!schema || !schema.$ref || !rootSchema) {
    return schema;
  }

  const refPath = schema.$ref;
  if (typeof refPath !== 'string' || !refPath.startsWith('#/')) {
    console.warn(`Unsupported or invalid $ref format: ${refPath}`);
    return schema;
  }

  const pathParts = refPath.substring(2).split('/');

  // Pydantic v1 used 'definitions', v2 uses '$defs'. Handle both.
  const definitions = rootSchema.definitions || rootSchema.$defs;
  if (!definitions) {
    console.warn(`Could not find 'definitions' or '$defs' in root schema to resolve $ref: ${refPath}`);
    return schema;
  }

  // Currently, our refs are simple, like '#/definitions/QueueConfig'.
  // The first part of the path should be 'definitions' or '$defs'.
  const defName = pathParts[1];
  const definition = definitions[defName];

  if (!definition) {
    console.warn(`Could not find definition for $ref: ${refPath}`);
    return schema;
  }

  // The resolved schema might have its own properties merged with the $ref schema.
  // For example: { "title": "My Ref", "$ref": "#/..." }. We merge them.
  const { $ref, ...rest } = schema;
  return { ...definition, ...rest };
};
