import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function HomePage() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const fetchFiles = async () => {
    try {
      setError(null);
      const response = await fetch('/api/configurations');
      if (!response.ok) {
        throw new Error('Failed to fetch configuration files.');
      }
      const data = await response.json();
      setFiles(data.files);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const handleLink = () => {
    if (selectedFile) {
      navigate(`/link/${selectedFile}`);
    }
  };

  const handleEdit = () => {
    if (selectedFile) {
      navigate(`/edit/${selectedFile}`);
    }
  };

  const handleAdd = async () => {
    const filename = prompt('Enter new filename (e.g., "my-config.json"):');
    if (!filename) {
      return; // User cancelled
    }

    if (!filename.endsWith('.json')) {
      alert('Filename must end with .json');
      return;
    }

    if (files.includes(filename)) {
      alert(`File "${filename}" already exists.`);
      return;
    }

    try {
      const response = await fetch(`/api/configurations/${filename}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([]), // Create with an empty array
      });

      if (!response.ok) {
        const errorBody = await response.json();
        throw new Error(errorBody.detail || 'Failed to create file.');
      }

      await fetchFiles(); // Refresh the file list
    } catch (err) {
      setError(`Failed to create file: ${err.message}`);
    }
  };

  const handleDelete = async () => {
    if (!selectedFile) {
      return;
    }

    if (window.confirm(`Are you sure you want to delete "${selectedFile}"?`)) {
      try {
        const response = await fetch(`/api/configurations/${selectedFile}`, {
          method: 'DELETE',
        });

        if (!response.ok) {
          const errorBody = await response.json();
          throw new Error(errorBody.detail || 'Failed to delete file.');
        }

        setSelectedFile(null); // Deselect the file
        await fetchFiles();   // Refresh the list
      } catch (err) {
        setError(`Failed to delete file: ${err.message}`);
      }
    }
  };

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div>
      <h2>Configuration Files</h2>
      <div className="file-list-container">
        {files.length === 0 ? (
          <p>No configuration files found.</p>
        ) : (
          <ul className="file-list">
            {files.map(file => (
              <li
                key={file}
                className={`file-item ${selectedFile === file ? 'selected' : ''}`}
                onClick={() => setSelectedFile(file)}
              >
                {file}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="action-buttons">
        <button onClick={handleAdd}>
          Add
        </button>
        <button onClick={handleLink} disabled={!selectedFile}>
          Link
        </button>
        <button onClick={handleEdit} disabled={!selectedFile}>
          Edit
        </button>
        <button onClick={handleDelete} disabled={!selectedFile} className="delete-button">
          Delete
        </button>
      </div>
    </div>
  );
}

export default HomePage;
