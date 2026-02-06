

// A field template that only renders the input, hiding label and description
// Used for inline compact rendering where labels are handled separately
export function InlineFieldTemplate(props) {
    const { children, id, registry } = props;
    const { cronErrors } = registry.formContext || {};

    let hasError = false;
    // Check if this is a cron field and has error
    if (id && id.endsWith('cronTrackingSchedule') && Array.isArray(cronErrors)) {
        // Extract index from id: ..._0_cronTrackingSchedule
        const match = id.match(/_(\d+)_cronTrackingSchedule$/);
        if (match) {
            const index = parseInt(match[1], 10);
            if (cronErrors[index]) {
                hasError = true;
            }
        }
    }

    const style = hasError ? { border: '1px solid #dc3545', borderRadius: '4px' } : {};

    return <div style={style}>{children}</div>;
}
