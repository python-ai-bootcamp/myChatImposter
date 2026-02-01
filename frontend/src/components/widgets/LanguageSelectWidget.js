import React from 'react';
import FilterableSelect from '../FilterableSelect';

/**
 * Language Select Widget - uses FilterableSelect under the hood.
 */
export function LanguageSelectWidget(props) {
    const [languages, setLanguages] = React.useState([]);
    const [loading, setLoading] = React.useState(true);

    // Fetch languages from API on mount
    React.useEffect(() => {
        fetch('/api/external/resources/languages')
            .then(res => res.json())
            .then(data => {
                setLanguages(data);
                setLoading(false);
            })
            .catch(err => {
                console.error('Failed to fetch languages:', err);
                setLoading(false);
            });
    }, []);

    // Build language options from API data
    const options = React.useMemo(() => {
        return languages.map(lang => ({
            value: lang.code,
            label: `${lang.name} (${lang.native_name})`,
            secondary: lang.code.toUpperCase()
        })).sort((a, b) => a.label.localeCompare(b.label));
    }, [languages]);

    return (
        <FilterableSelect
            value={props.value}
            onChange={props.onChange}
            options={options}
            placeholder="Select language..."
            loading={loading}
        />
    );
}
