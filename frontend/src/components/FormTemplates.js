import React from 'react';

export function CustomFieldTemplate(props) {
  const { id, label, children, required, rawErrors = [], help, description, classNames } = props;

  // For checkboxes, the label is part of the children, so we don't render our own label.
  if (props.schema.type === 'boolean') {
    return (
      <div className={classNames}>
        {children}
        {rawErrors.length > 0 && <ul>{rawErrors.map((error, i) => <li key={i} className="text-danger">{error}</li>)}</ul>}
        {help}
      </div>
    );
  }

  // Don't render a label for the top-level object
  if (props.schema.type === 'object' && !props.formContext.root) {
      return children;
  }


  return (
    <div className={classNames} style={{ display: 'flex', marginBottom: '1rem', alignItems: 'flex-start' }}>
      <label htmlFor={id} style={{ width: '30%', textAlign: 'left', paddingRight: '1rem', boxSizing: 'border-box' }}>
        {label}{required ? '*' : null}
      </label>
      <div style={{ width: '70%', boxSizing: 'border-box' }}>
        {description}
        {children}
        {rawErrors.length > 0 && <ul>{rawErrors.map((error, i) => <li key={i} className="text-danger">{error}</li>)}</ul>}
        {help}
      </div>
    </div>
  );
}

export function CustomObjectFieldTemplate(props) {
  return (
    <div>
      {props.title && <h3>{props.title}</h3>}
      {props.description}
      {props.properties.map(element => (
        <div className="property-wrapper" key={element.content.key}>
          {element.content}
        </div>
      ))}
    </div>
  );
}
