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

  // Custom widget for Group Selection
  const GroupSelectorWidget = (props) => {
    const [filter, setFilter] = useState('');

    // Determine current value
    const currentVal = props.value || '';

    // Find display name for current value if not in available list
    const currentGroup = availableGroups.find(g => g.id === currentVal);

    const filteredGroups = availableGroups.filter(g =>
        (g.subject || '').toLowerCase().includes(filter.toLowerCase()) ||
        g.id.toLowerCase().includes(filter.toLowerCase())
    );

    return (
      <div>
        <div style={{ marginBottom: '10px' }}>
            <input
                type="text"
                placeholder="Search groups..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                style={{ width: '100%', padding: '5px', marginBottom: '5px' }}
            />
            {filter && (
                <div style={{ maxHeight: '150px', overflowY: 'auto', border: '1px solid #ccc' }}>
                    {filteredGroups.map(g => (
                        <div
                            key={g.id}
                            onClick={() => {
                                props.onChange(g.id);
                                // Hacky way to set the display name in the sibling field if it exists
                                // In a real RJSF custom field we'd do this better, but here we might rely on the user manually checking?
                                // Actually, we need to populate 'displayName' as well.
                                // Since this widget only controls one field, we can't easily set the other.
                                // We will rely on the user to select the group, and we will try to autofill the name if possible,
                                // but RJSF structure makes cross-field updates tricky without a custom field template.
                                // Alternative: Store the whole object? No, schema defines separate string fields.
                                setFilter('');
                            }}
                            style={{ padding: '5px', cursor: 'pointer', borderBottom: '1px solid #eee' }}
                        >
                            {g.subject} <small>({g.id})</small>
                        </div>
                    ))}
                </div>
            )}
        </div>
        <div>
            <strong>Selected Group ID:</strong> {currentVal}
            {currentGroup && <div style={{color: 'green'}}>Selected: {currentGroup.subject}</div>}
        </div>
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
                    groupIdentifier: { type: "string", title: "Group ID" },
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
