import React from 'react';
import FilterableSelect from '../FilterableSelect';
import { useTheme } from '../../contexts/ThemeContext';

// Get UTC offset string for a timezone (e.g., "+02:00", "-05:00")
function getTimezoneOffset(timezone) {
    try {
        const now = new Date();
        const formatter = new Intl.DateTimeFormat('en-US', {
            timeZone: timezone,
            timeZoneName: 'shortOffset'
        });
        const parts = formatter.formatToParts(now);
        const offsetPart = parts.find(p => p.type === 'timeZoneName');
        if (offsetPart) {
            // Convert "GMT+2" to "+02:00" format
            const value = offsetPart.value;
            if (value === 'GMT') return '+00:00';
            const match = value.match(/GMT([+-])(\d+)(?::(\d+))?/);
            if (match) {
                const sign = match[1];
                const hours = match[2].padStart(2, '0');
                const mins = match[3] || '00';
                return `${sign}${hours}:${mins}`;
            }
            return value.replace('GMT', '');
        }
    } catch (e) {
        return '';
    }
    return '';
}

/**
 * Timezone Select Widget - uses FilterableSelect under the hood.
 */
export function TimezoneSelectWidget(props) {
    const [timezones, setTimezones] = React.useState([]);
    const [loading, setLoading] = React.useState(true);

    const { isDarkMode } = useTheme();

    React.useEffect(() => {
        fetch('/api/external/resources/timezones')
            .then(res => {
                if (!res.ok) throw new Error('Network response was not ok');
                return res.json();
            })
            .then(data => {
                setTimezones(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to fetch timezones:", err);
                setLoading(false);
            });
    }, []);

    // Build timezone options with offsets
    const options = React.useMemo(() => {
        return timezones.map(tz => ({
            value: tz,
            label: tz.replace(/_/g, ' '),
            secondary: getTimezoneOffset(tz)
        })).sort((a, b) => {
            // Sort by offset, then alphabetically
            const offsetA = a.secondary || '+00:00';
            const offsetB = b.secondary || '+00:00';
            if (offsetA !== offsetB) return offsetA.localeCompare(offsetB);
            return a.label.localeCompare(b.label);
        });
    }, [timezones]);

    return (
        <FilterableSelect
            value={props.value}
            onChange={props.onChange}
            options={options}
            placeholder="Select timezone..."
            loading={loading}
            darkMode={props.formContext?.darkMode || props.darkMode || isDarkMode}
        />
    );
}
