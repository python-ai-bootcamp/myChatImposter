import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import Form from '@rjsf/core';
import validator from '@rjsf/validator-ajv8';

const GroupTrackingPage = () => {
  const { userId } = useParams();
  const [config, setConfig] = useState(null);
  const [availableGroups, setAvailableGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch configuration and active groups on load
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Fetch config
        const configRes = await fetch(`/api/configurations/${userId}`);
        if (!configRes.ok) throw new Error("Failed to fetch configuration");
        const configData = await configRes.json();
        setConfig(configData);

        // Fetch groups
        const groupsRes = await fetch(`/chatbot/${userId}/groups`);
        if (groupsRes.ok) {
            const groupsData = await groupsRes.json();
            setAvailableGroups(groupsData.groups || []);
        } else {
            console.warn("Could not fetch active groups, maybe bot is not connected.");
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [userId]);

  const handleSave = async ({ formData }) => {
    try {
      const res = await fetch(`/api/configurations/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!res.ok) throw new Error("Failed to save configuration");

      // Reload the bot to apply changes
      await fetch(`/chatbot/${userId}/reload`, { method: 'POST' });

      setConfig(formData);
      alert('Configuration saved and bot reloaded!');
    } catch (err) {
      alert(`Error saving: ${err.message}`);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  // Custom widget for Group Selection (Autocomplete style)
  const GroupSelectorWidget = (props) => {
    // Current selected ID from props
    const selectedId = props.value || '';

    // Find the currently selected group object to get its name
    const selectedGroup = availableGroups.find(g => g.id === selectedId);

    // State for the input text.
    // If we have a selection, show its name. Otherwise empty.
    // If user is typing, we show what they type.
    // We use a separate state 'inputValue' to control the text box.
    const [inputValue, setInputValue] = useState(selectedGroup ? selectedGroup.subject : selectedId);
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    // Update input value if external props change (e.g. initial load)
    useEffect(() => {
        if (selectedGroup) {
            setInputValue(selectedGroup.subject);
        } else if (selectedId) {
            setInputValue(selectedId); // Fallback to ID if not found
        }
    }, [selectedId, selectedGroup]);

    // Filter groups based on input value
    // We filter only if the menu is open (user is interacting) to avoid confusing behavior
    // but typically autocomplete filters based on current text.
    const filteredGroups = availableGroups.filter(g =>
        (g.subject || '').toLowerCase().includes(inputValue.toLowerCase())
    );

    const handleInputChange = (e) => {
        setInputValue(e.target.value);
        setIsMenuOpen(true);
        // We do NOT call props.onChange here because we want to commit only on selection
        // or we could clear it?
        // If user clears text, we should clear selection.
        if (e.target.value === '') {
            props.onChange(undefined);
        }
    };

    const handleSelect = (group) => {
        setInputValue(group.subject);
        props.onChange(group.id);
        setIsMenuOpen(false);
    };

    return (
      <div style={{ position: 'relative' }}>
        <input
            type="text"
            placeholder="Type group name..."
            value={inputValue}
            onChange={handleInputChange}
            onFocus={() => setIsMenuOpen(true)}
            onBlur={() => {
                // Delay hiding menu to allow click event to register
                setTimeout(() => setIsMenuOpen(false), 200);
            }}
            style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
        />
        {isMenuOpen && filteredGroups.length > 0 && (
            <div style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                maxHeight: '200px',
                overflowY: 'auto',
                border: '1px solid #ccc',
                backgroundColor: '#fff',
                zIndex: 1000
            }}>
                {filteredGroups.map(g => (
                    <div
                        key={g.id}
                        onMouseDown={() => handleSelect(g)} // Use onMouseDown to trigger before onBlur
                        style={{ padding: '8px', cursor: 'pointer', borderBottom: '1px solid #eee' }}
                        className="group-option"
                    >
                        <strong>{g.subject}</strong> <br/>
                        <small style={{ color: '#666' }}>{g.id}</small>
                    </div>
                ))}
            </div>
        )}
        {selectedId && (
            <div style={{ marginTop: '5px', fontSize: '0.85em', color: '#555' }}>
                ID: {selectedId}
            </div>
        )}
      </div>
    );
  };

  // Schema Definition for the form
  const schema = {
    type: "object",
    properties: {
        periodic_group_tracking: {
            type: "array",
            title: "Tracked Groups",
            items: {
                type: "object",
                properties: {
                    groupIdentifier: { type: "string", title: "Group Name (Search)" },
                    displayName: { type: "string", title: "Display Name" },
                    cronTrackingSchedule: { type: "string", title: "Cron Schedule (e.g. '0 * * * *')" }
                },
                required: ["groupIdentifier", "cronTrackingSchedule"]
            }
        }
    }
  };

  const uiSchema = {
    periodic_group_tracking: {
        items: {
            groupIdentifier: {
                "ui:widget": GroupSelectorWidget
            },
            displayName: {
                "ui:help": "Friendly name for the group. Will be autofilled on save if empty."
            }
        }
    }
  };

  // Pre-process data before save to ensure display name matches ID if possible
  const onSubmit = (data) => {
      const newData = { ...config, ...data.formData };
      newData.periodic_group_tracking = newData.periodic_group_tracking.map(item => {
          const group = availableGroups.find(g => g.id === item.groupIdentifier);
          if (group && !item.displayName) {
              item.displayName = group.subject;
          }
          return item;
      });
      handleSave({ formData: newData });
  };

  return (
    <div style={{ padding: '20px' }}>
      <h2>Group Tracking for {userId}</h2>
      <Link to="/">Back to Home</Link>
      <hr />

      <p>Configure which groups to actively track and format for context.</p>

      <Form
        schema={schema}
        uiSchema={uiSchema}
        formData={{ periodic_group_tracking: config.periodic_group_tracking || [] }}
        validator={validator}
        onSubmit={onSubmit}
      />
    </div>
  );
};

export default GroupTrackingPage;
