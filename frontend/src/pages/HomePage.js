import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

function HomePage() {
  const [files, setFiles] = useState([]);
  const [error, setError] = useState(null);

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

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div>
      <h2>Configuration Files</h2>
      {files.length === 0 ? (
        <p>No configuration files found.</p>
      ) : (
        <ul>
          {files.map(file => (
            <li key={file}>
              {file}
              <Link to={`/link/${file}`}><button>Link</button></Link>
              <Link to={`/edit/${file}`}><button>Edit</button></Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default HomePage;
