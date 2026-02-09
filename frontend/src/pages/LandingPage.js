import React from 'react';

const LandingPage = () => {
    return (
        <div className="landing-page">
            <style>{`
                .landing-page {
                    position: fixed;
                    top: 60px;
                    bottom: 0;
                    left: 0;
                    width: 100%;
                    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                    color: #e2e8f0;
                    font-family: 'Inter', sans-serif;
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    gap: 4vh;
                    box-sizing: border-box;
                    z-index: 0;
                }

                .hero-section {
                    text-align: center;
                    max-width: 1000px;
                    animation: fadeIn 1s ease-out;
                    z-index: 1; /* Ensure text is above shapes */
                }

                .hero-title {
                    font-size: 4rem;
                    font-weight: 800;
                    margin-bottom: 1.5rem;
                    line-height: 1.3;
                    padding-bottom: 10px;
                    background: linear-gradient(to right, #c084fc, #6366f1, #3b82f6);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    filter: drop-shadow(0 0 2em rgba(99, 102, 241, 0.3));
                }

                .hero-subtitle {
                    font-size: 1.5rem;
                    color: #94a3b8;
                    margin-bottom: 0;
                    line-height: 1.6;
                    max-width: 700px;
                    margin-left: auto;
                    margin-right: auto;
                }

                .features-grid {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr); /* Force 4 columns for single line */
                    gap: 2rem;
                    padding: 0 2rem;
                    max-width: 1200px;
                    width: 100%;
                    box-sizing: border-box;
                    z-index: 1;
                }

                .feature-card {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(10px);
                    padding: 1rem;
                    border-radius: 1.5rem;
                    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                    position: relative;
                    overflow: hidden;
                }

                .feature-card:hover {
                    transform: translateY(-10px);
                    background: rgba(255, 255, 255, 0.07);
                    border-color: rgba(99, 102, 241, 0.3);
                    box-shadow: 0 20px 40px -15px rgba(99, 102, 241, 0.2);
                }

                .feature-icon {
                    font-size: 2.5rem;
                    margin-bottom: 1.5rem;
                    background: linear-gradient(135deg, #818cf8, #c084fc);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }

                .feature-title {
                    font-size: 1.5rem;
                    font-weight: 700;
                    margin-bottom: 1rem;
                    color: #f8fafc;
                }

                .feature-desc {
                    color: #cbd5e1;
                    line-height: 1.6;
                }

                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                /* Floating shapes background */
                .shape {
                    position: absolute;
                    filter: blur(80px);
                    z-index: 0;
                    opacity: 0.4;
                    pointer-events: none;
                }
                .shape-1 {
                    top: -10%;
                    left: -10%;
                    width: 50vw;
                    height: 50vw;
                    background: radial-gradient(circle, #4f46e5 0%, transparent 70%);
                }
                .shape-2 {
                    bottom: -10%;
                    right: -10%;
                    width: 40vw;
                    height: 40vw;
                    background: radial-gradient(circle, #ec4899 0%, transparent 70%);
                }
            `}</style>

            <div className="shape shape-1" />
            <div className="shape shape-2" />

            <div className="hero-section">
                <h1 className="hero-title">
                    My WhatsApp Bot Assistant
                </h1>
                <p className="hero-subtitle">
                    Create helpful intelligent AI driven bots to manage your WhatsApp clutter.
                </p>
            </div>

            <div className="features-grid">
                <div className="feature-card">
                    <div className="feature-icon">
                        <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ verticalAlign: 'middle' }}>
                            <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2ZM20 16H6L4 18V4H20V16Z"
                                stroke="url(#advisorGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="url(#advisorFill)" />
                            <path d="M8 9H16M8 13H12"
                                stroke="url(#advisorGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                            <defs>
                                <linearGradient id="advisorGradient" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                                    <stop stopColor="#818cf8" />
                                    <stop offset="1" stopColor="#c084fc" />
                                </linearGradient>
                                <linearGradient id="advisorFill" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                                    <stop stopColor="#818cf8" stopOpacity="0.2" />
                                    <stop offset="1" stopColor="#c084fc" stopOpacity="0.2" />
                                </linearGradient>
                            </defs>
                        </svg>
                    </div>
                    <h3 className="feature-title">AI Chat Advisor</h3>
                    <p className="feature-desc">
                        Navigate tricky conversations with confidence. Your AI analyzes chat history and professional knowledge to suggest the perfect response.
                    </p>
                </div>

                <div className="feature-card">
                    <div className="feature-icon">
                        <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ verticalAlign: 'middle' }}>
                            <path d="M12 2A2 2 0 0 1 14 4V6H10V4A2 2 0 0 1 12 2M21 16L22.5 15.5L21.5 12.5L20 13V12C20 8.69 16.42 6 12 6C7.58 6 4 8.69 4 12V13L2.5 12.5L1.5 15.5L3 16V22H21V16ZM15 13C16.1 13 17 13.9 17 15C17 16.1 16.1 17 15 17C13.9 17 13 16.1 13 15C13 13.9 13.9 13 15 13ZM9 13C10.1 13 11 13.9 11 15C11 16.1 10.1 17 9 17C7.9 17 7 16.1 7 15C7 13.9 7.9 13 9 13Z"
                                stroke="url(#robotGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="url(#robotFill)" />
                            <defs>
                                <linearGradient id="robotGradient" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                                    <stop stopColor="#34d399" />
                                    <stop offset="1" stopColor="#3b82f6" />
                                </linearGradient>
                                <linearGradient id="robotFill" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                                    <stop stopColor="#34d399" stopOpacity="0.2" />
                                    <stop offset="1" stopColor="#3b82f6" stopOpacity="0.2" />
                                </linearGradient>
                            </defs>
                        </svg>
                    </div>
                    <h3 className="feature-title">Automatic Bot Reply</h3>
                    <p className="feature-desc">
                        Don't let endless notifications drain your energy. Automate responses to specific contacts and stay focused.
                    </p>
                </div>

                <div className="feature-card">
                    <div className="feature-icon">🕵️</div>
                    <h3 className="feature-title">Group Tracking</h3>
                    <p className="feature-desc">
                        Never miss your kid's school event ever again. Let AI scan your groups and turn important dates into calendar invites automatically.
                    </p>
                </div>

                <div className="feature-card">
                    <div className="feature-icon">
                        <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ verticalAlign: 'middle' }}>
                            <path d="M12 2L4 5V11.09C4 16.14 7.41 20.53 12 22C16.59 20.53 20 16.14 20 11.09V5L12 2Z"
                                stroke="url(#shieldGradient)"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                fill="url(#shieldFill)" />
                            <defs>
                                <linearGradient id="shieldGradient" x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
                                    <stop stopColor="#6366f1" />
                                    <stop offset="1" stopColor="#ec4899" />
                                </linearGradient>
                                <linearGradient id="shieldFill" x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
                                    <stop stopColor="#6366f1" stopOpacity="0.2" />
                                    <stop offset="1" stopColor="#ec4899" stopOpacity="0.2" />
                                </linearGradient>
                            </defs>
                        </svg>
                    </div>
                    <h3 className="feature-title">Kid Safety</h3>
                    <p className="feature-desc">
                        Command bots to scan your beloved child correspondence for negative WhatsApp interactions.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default LandingPage;
