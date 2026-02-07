import React, { useState, useEffect } from 'react';
import Select from 'react-select';

const CountrySelectWidget = ({ value, onChange, disabled }) => {
    const [countries, setCountries] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/external/resources/countries')
            .then(res => res.json())
            .then(data => {
                // Map to react-select format
                const options = data.map(c => ({
                    value: c.code,
                    label: `${c.flag} ${c.name}`
                }));
                setCountries(options);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to load countries", err);
                setLoading(false);
            });
    }, []);

    const handleChange = (selectedOption) => {
        onChange(selectedOption ? selectedOption.value : '');
    };

    const selectedOption = countries.find(c => c.value === value);

    return (
        <Select
            options={countries}
            value={selectedOption}
            onChange={handleChange}
            isDisabled={disabled || loading}
            isLoading={loading}
            placeholder="Select Country..."
            isClearable
            styles={{
                control: (base) => ({
                    ...base,
                    minHeight: '30px',
                    height: '30px',
                }),
                valueContainer: (base) => ({
                    ...base,
                    height: '30px',
                    padding: '0 8px',
                }),
                input: (base) => ({
                    ...base,
                    margin: '0px',
                    padding: '0px',
                }),
                indicatorsContainer: (base) => ({
                    ...base,
                    height: '30px',
                }),
            }}
        />
    );
};

export default CountrySelectWidget;
