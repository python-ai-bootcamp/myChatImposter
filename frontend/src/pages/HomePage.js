import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

function HomePage() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchFiles = async () => {
      try {
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
        <button onClick={handleLink} disabled={!selectedFile}>
          Link
        </button>
        <button onClick={handleEdit} disabled={!selectedFile}>
          Edit
        </button>
      </div>
    </div>
  );
}

export default HomePage;
