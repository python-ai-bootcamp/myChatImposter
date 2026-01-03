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
        let configData = await configRes.json();

        // Normalize config data: Handle legacy array format
        if (Array.isArray(configData)) {
            configData = configData.length > 0 ? configData[0] : {};
        }

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
      if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail ? JSON.stringify(errData.detail) : "Failed to save configuration");
      }

      // Reload the bot to apply changes
      await fetch(`/chatbot/${userId}/reload`, { method: 'POST' });

      // Update local state, preserving structure
      // Ensure we keep it as an object
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
    const selectedId = props.value || '';
    const selectedGroup = availableGroups.find(g => g.id === selectedId);

    // If we have a selected group, the input should allow searching/changing.
    // If we have a selection, we verify if the input text matches.
    const [inputValue, setInputValue] = useState(selectedGroup ? selectedGroup.subject : (selectedId || ''));
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    useEffect(() => {
        if (selectedGroup) {
            setInputValue(selectedGroup.subject);
        } else if (selectedId && !selectedGroup) {
            setInputValue(selectedId);
        }
    }, [selectedId, selectedGroup]);

    const filteredGroups = availableGroups.filter(g =>
        (g.subject || '').toLowerCase().includes(inputValue.toLowerCase())
    );

    const handleInputChange = (e) => {
        setInputValue(e.target.value);
        setIsMenuOpen(true);
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
      <div style={{ position: 'relative', marginBottom: '10px' }}>
        <input
            type="text"
            placeholder="Type group name..."
            value={inputValue}
            onChange={handleInputChange}
            onFocus={() => setIsMenuOpen(true)}
            onBlur={() => setTimeout(() => setIsMenuOpen(false), 200)}
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
                        onMouseDown={() => handleSelect(g)}
                        style={{ padding: '8px', cursor: 'pointer', borderBottom: '1px solid #eee' }}
                        className="group-option"
                    >
                        <strong>{g.subject}</strong> <br/>
                        <small style={{ color: '#666' }}>{g.id}</small>
                    </div>
                ))}
            </div>
        )}

        {/* Read-only display of ID and Name as requested */}
        {selectedId && (
            <div style={{ marginTop: '8px', padding: '10px', backgroundColor: '#f9f9f9', borderRadius: '4px', border: '1px solid #ddd' }}>
                 <div style={{ fontWeight: 'bold', fontSize: '1.1em' }}>
                    {selectedGroup ? selectedGroup.subject : 'Unknown Group Name'}
                 </div>
                 <div style={{ fontSize: '0.85em', color: '#666', marginTop: '4px' }}>
                    ID: {selectedId}
                 </div>
            </div>
        )}
      </div>
    );
  };

  const validateCron = (formData, errors) => {
      if (formData.periodic_group_tracking) {
        formData.periodic_group_tracking.forEach((item, index) => {
            const cron = item.cronTrackingSchedule;
            if (cron) {
                const parts = cron.trim().split(/\s+/);
                // Basic check: 5 parts
                if (parts.length !== 5) {
                     errors.periodic_group_tracking[index].cronTrackingSchedule.addError("Invalid cron expression: must have exactly 5 parts (minute hour day month day-of-week).");
                }
                // Check for valid characters allowed in cron
                else {
                    const validChars = /^[0-9*/,\-]+$/;
                    if (!parts.every(p => validChars.test(p))) {
                        errors.periodic_group_tracking[index].cronTrackingSchedule.addError("Invalid characters in cron expression. Allowed: 0-9 * / , -");
                    }
                }
            }
        });
      }
      return errors;
  };

  const schema = {
    type: "object",
    properties: {
        periodic_group_tracking: {
            type: "array",
            title: "Tracked Groups",
            items: {
                type: "object",
                properties: {
                    groupIdentifier: { type: "string", title: "Group Selection" },
                    displayName: { type: "string", title: "Display Name" },
                    cronTrackingSchedule: { type: "string", title: "Cron Schedule" }
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
                "ui:widget": "hidden"
            },
            cronTrackingSchedule: {
                "ui:placeholder": "e.g. 0/5 * * * *"
            }
        }
    }
  };

  const onSubmit = (data) => {
      // Ensure config is an object before merging
      const baseConfig = Array.isArray(config) ? (config[0] || {}) : (config || {});
      const newData = { ...baseConfig, ...data.formData };

      newData.periodic_group_tracking = newData.periodic_group_tracking.map(item => {
          const group = availableGroups.find(g => g.id === item.groupIdentifier);
          if (group) {
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
        formData={{ periodic_group_tracking: config ? (Array.isArray(config) ? (config[0]?.periodic_group_tracking || []) : (config.periodic_group_tracking || [])) : [] }}
        validator={validator}
        customValidate={validateCron}
        onSubmit={onSubmit}
      />
    </div>
  );
};

export default GroupTrackingPage;
