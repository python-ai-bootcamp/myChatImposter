

// A field template that only renders the input, hiding label and description
// Used for inline compact rendering where labels are handled separately
export function InlineFieldTemplate(props) {
    const { children } = props;
    return children;
}
