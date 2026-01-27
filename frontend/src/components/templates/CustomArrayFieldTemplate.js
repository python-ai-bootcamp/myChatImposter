import React from 'react';

export function CustomArrayFieldTemplate(props) {
    const btnStyle = {
        padding: '0.1rem 0.4rem',
        fontSize: '0.8rem',
        lineHeight: 1.2,
        border: '1px solid #ccc',
        borderRadius: '3px',
        cursor: 'pointer'
    };
    const disabledBtnStyle = {
        ...btnStyle,
        cursor: 'not-allowed',
        backgroundColor: '#f8f8f8',
        color: '#ccc',
    };

    return (
        <div style={{ border: '1px solid #ccc', borderRadius: '4px', padding: '1rem' }}>
            {props.title && (
                <h3 style={{ margin: 0, padding: 0, borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem', textAlign: 'left' }}>
                    {props.title}
                </h3>
            )}
            {props.items &&
                props.items.map(element => (
                    <div key={element.key} style={{ marginBottom: '0.5rem', display: 'flex', alignItems: 'center' }}>
                        <span style={{ marginRight: '0.5rem' }}>•</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div>{element.children}</div>
                            <div style={{ display: 'flex', gap: '0.3rem' }}>
                                <button
                                    type="button"
                                    onClick={element.onReorderClick(element.index, element.index - 1)}
                                    style={element.hasMoveUp ? btnStyle : disabledBtnStyle}
                                    disabled={!element.hasMoveUp}
                                >
                                    ↑
                                </button>
                                <button
                                    type="button"
                                    onClick={element.onReorderClick(element.index, element.index + 1)}
                                    style={element.hasMoveDown ? btnStyle : disabledBtnStyle}
                                    disabled={!element.hasMoveDown}
                                >
                                    ↓
                                </button>
                                <button
                                    type="button"
                                    onClick={element.onDropIndexClick(element.index)}
                                    style={element.hasRemove ? btnStyle : disabledBtnStyle}
                                    disabled={!element.hasRemove}
                                >
                                    -
                                </button>
                            </div>
                        </div>
                    </div>
                ))}

            {props.canAdd && (
                <button type="button" onClick={props.onAddClick} style={{ ...btnStyle, padding: '0.3rem 0.6rem', marginTop: '0.5rem' }}>
                    + Add
                </button>
            )}
        </div>
    );
}
