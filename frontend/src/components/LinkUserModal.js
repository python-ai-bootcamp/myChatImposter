import React from 'react';

const modalOverlayStyle = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000
};

const modalContentStyle = {
    backgroundColor: '#1a1a1a',
    padding: '0',
    borderRadius: '45px',
    maxWidth: '320px',
    width: '90%',
    textAlign: 'center',
    boxShadow: '0 25px 50px rgba(0,0,0,0.5), inset 0 0 0 3px #333',
    position: 'relative',
    overflow: 'hidden',
    border: '8px solid #1a1a1a'
};

const phoneScreenStyle = {
    backgroundColor: '#000',
    borderRadius: '35px',
    margin: '10px',
    padding: '20px',
    minHeight: '500px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative'
};

const notchStyle = {
    position: 'absolute',
    top: '10px',
    left: '50%',
    transform: 'translateX(-50%)',
    width: '100px',
    height: '25px',
    backgroundColor: '#1a1a1a',
    borderRadius: '20px'
};

const homeIndicatorStyle = {
    position: 'absolute',
    bottom: '8px',
    left: '50%',
    transform: 'translateX(-50%)',
    width: '130px',
    height: '5px',
    backgroundColor: '#555',
    borderRadius: '3px'
};

function LinkUserModal({ linkingBotId, linkStatus, qrCode, onClose }) {
    if (!linkingBotId) {
        return null;
    }

    return (
        <div style={modalOverlayStyle} onClick={onClose}>
            <div style={modalContentStyle} onClick={e => e.stopPropagation()}>
                <div style={phoneScreenStyle}>
                    {/* Notch */}
                    <div style={notchStyle}></div>

                    {/* Close button */}
                    <button
                        onClick={onClose}
                        style={{
                            position: 'absolute',
                            top: '45px',
                            right: '15px',
                            background: 'rgba(255,255,255,0.2)',
                            border: 'none',
                            fontSize: '1.2rem',
                            cursor: 'pointer',
                            color: '#fff',
                            width: '30px',
                            height: '30px',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        &times;
                    </button>

                    {/* Content */}
                    <div style={{ marginTop: '30px', color: '#fff' }}>
                        <h3 style={{ margin: '0 0 10px 0', color: '#fff', fontSize: '1.1rem' }}>
                            {linkingBotId}
                        </h3>
                        <p style={{ margin: '0 0 20px 0', color: '#888', fontSize: '0.85rem' }}>
                            {linkStatus || 'Initializing...'}
                        </p>

                        {qrCode ? (
                            <div>
                                <div style={{
                                    backgroundColor: '#fff',
                                    padding: '15px',
                                    borderRadius: '12px',
                                    display: 'inline-block'
                                }}>
                                    <img
                                        src={qrCode}
                                        alt="QR Code"
                                        style={{
                                            width: '180px',
                                            height: '180px',
                                            display: 'block'
                                        }}
                                    />
                                </div>
                                <p style={{ fontSize: '0.8rem', color: '#888', marginTop: '15px' }}>
                                    Scan with WhatsApp
                                </p>
                            </div>
                        ) : (
                            <div style={{
                                padding: '40px 20px',
                                color: linkStatus === 'connected' ? '#4ade80' : '#888'
                            }}>
                                {linkStatus === 'connected' ? (
                                    <div>
                                        <div style={{ fontSize: '3rem', marginBottom: '10px' }}>✓</div>
                                        <div>Connected!</div>
                                    </div>
                                ) : (
                                    <div>
                                        <div style={{
                                            width: '40px',
                                            height: '40px',
                                            border: '3px solid #444',
                                            borderTop: '3px solid #888',
                                            borderRadius: '50%',
                                            margin: '0 auto 15px',
                                            animation: 'spin 1s linear infinite'
                                        }}></div>
                                        <div>Connecting...</div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Home Indicator */}
                    <div style={homeIndicatorStyle}></div>
                </div>
            </div>
        </div>
    );
}

export default LinkUserModal;
