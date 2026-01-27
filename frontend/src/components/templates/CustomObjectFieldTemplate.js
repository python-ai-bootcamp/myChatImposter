import React from 'react';

export function CustomObjectFieldTemplate(props) {
    // A more robust way to detect the provider settings objects that need special styling.
    const isChatProviderSettings = props.properties.some(p => p.name === 'allow_group_messages');
    const isLlmProviderSettings = props.uiSchema['ui:options']?.box === 'LlmProviderSettings';
    const shouldHaveBorder = isChatProviderSettings; // LlmProviderSettings is now handled by the wrapper

    const fieldsetStyle = {
        border: shouldHaveBorder ? '1px solid #ccc' : 'none',
        borderRadius: '4px',
        padding: shouldHaveBorder ? '1rem' : '0',
        margin: 0,
        width: '100%',
        marginTop: shouldHaveBorder ? '0.5rem' : '0',
        display: 'table',
        borderCollapse: 'collapse'
    };

    // Determine the correct title to display.
    let title = props.title;
    if (isLlmProviderSettings) {
        // The title is now handled by the wrapper in CustomFieldTemplate
        title = null;
    } else if (isChatProviderSettings) {
        title = 'ChatProviderSettings';
    }

    // Hide the title for the inner oneOf selection, but show our custom one.
    // This is the definitive fix: explicitly check for the title we want to hide.
    // Also hide if title is empty or whitespace-only, or if it's "API Key Source" (shown as label instead)
    const isLlmModeTitle = props.title === 'Llm Mode';
    const isTitleEmpty = !title || (typeof title === 'string' && title.trim() === '');
    const isApiKeySourceTitle = props.title === 'API Key Source';
    const shouldShowTitle = !isLlmModeTitle && !isTitleEmpty && !isApiKeySourceTitle && ((title && shouldHaveBorder) || (props.title && !isLlmProviderSettings && props.title !== 'Respond Using Llm'));


    return (
        <fieldset style={fieldsetStyle}>
            {shouldShowTitle && (
                <h3 style={{ margin: 0, padding: 0, borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem', textAlign: 'left' }}>
                    {title}
                </h3>
            )}

            {props.description}
            {props.properties.map(element => (
                <React.Fragment key={element.content.key}>
                    {element.content}
                </React.Fragment>
            ))}
        </fieldset>
    );
}
