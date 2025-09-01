import React from 'react';

export function CustomFieldTemplate(props) {
  const { id, label, children, required, rawErrors = [], help, description, classNames } = props;

  // Don't render a label for the top-level object title, it's handled by the ObjectFieldTemplate
  if (props.schema.type === 'object') {
      return children;
  }

  // Special handling for booleans to have checkbox on the left of the label text
  if (props.schema.type === 'boolean') {
    return (
        <div className={classNames} style={{ display: 'flex', marginBottom: '1rem', alignItems: 'center' }}>
            <div style={{ width: '30%', textAlign: 'left', paddingRight: '1rem', boxSizing: 'border-box' }}>
                {/* The checkbox widget is in `children` */}
                {children}
            </div>
            <label htmlFor={id} style={{ width: '70%', boxSizing: 'border-box', margin: 0 }}>
                {label}{required ? '*' : null}
            </label>
        </div>
    );
  }


  return (
    <div className={classNames} style={{ display: 'flex', marginBottom: '1rem', alignItems: 'center' }}>
      <label htmlFor={id} style={{ width: '30%', textAlign: 'left', paddingRight: '1rem', boxSizing: 'border-box', margin: 0 }}>
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
    <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
      {/* Render the title of the object, aligned with the right column */}
      {props.title && (
         <div style={{ display: 'flex', marginBottom: '1rem', alignItems: 'center' }}>
            <div style={{ width: '30%', paddingRight: '1rem', boxSizing: 'border-box' }}></div>
            <div style={{ width: '70%', boxSizing: 'border-box' }}>
                <h3 style={{ margin: 0, padding: 0, borderBottom: '1px solid #eee', paddingBottom: '0.5rem' }}>{props.title}</h3>
            </div>
         </div>
      )}

      {props.description}

      {/* Render the properties of the object */}
      {props.properties.map(element => (
        <div className="property-wrapper" key={element.content.key}>
          {element.content}
        </div>
      ))}
    </fieldset>
  );
}
