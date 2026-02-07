import React from 'react';

const LandingPage = () => {
    return (
        <div className="landing-page">
            <style>{`
                .landing-page {
                    min-height: 100vh;
                    width: 100%;
                    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                    color: #e2e8f0;
                    font-family: 'Inter', sans-serif;
                    overflow-x: hidden;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }

                .hero-section {
                    text-align: center;
                    padding: 8rem 2rem 4rem;
                    max-width: 1000px;
                    animation: fadeIn 1s ease-out;
                }

                .hero-title {
                    font-size: 4rem;
                    font-weight: 800;
                    margin-bottom: 1.5rem;
                    line-height: 1.1;
                    background: linear-gradient(to right, #c084fc, #6366f1, #3b82f6);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    filter: drop-shadow(0 0 2em rgba(99, 102, 241, 0.3));
                }

                .hero-subtitle {
                    font-size: 1.5rem;
                    color: #94a3b8;
                    margin-bottom: 3rem;
                    line-height: 1.6;
                    max-width: 700px;
                    margin-left: auto;
                    margin-right: auto;
                }

                .features-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                    gap: 2rem;
                    padding: 2rem;
                    max-width: 1200px;
                    width: 100%;
                    box-sizing: border-box;
                    margin-bottom: 5rem;
                }

                .feature-card {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(10px);
                    padding: 2.5rem;
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
                    Master Your <br />
                    Digital Presence
                </h1>
                <p className="hero-subtitle">
                    Create intelligent, personality-driven AI imposters for WhatsApp.
                    Manage your bot farm with military-grade precision and effortless style.
                </p>
            </div>

            <div className="features-grid">
                <div className="feature-card">
                    <div className="feature-icon">🤖</div>
                    <h3 className="feature-title">AI Personalities</h3>
                    <p className="feature-desc">
                        Forge unique identities. From helpful assistants to chaotic neutral agents,
                        control the narrative with advanced prompt engineering.
                    </p>
                </div>

                <div className="feature-card">
                    <div className="feature-icon">⚡</div>
                    <h3 className="feature-title">Instant Deployment</h3>
                    <p className="feature-desc">
                        Link devices via QR code in seconds. Our optimised infrastructure
                        handles the heavy lifting so you don't have to.
                    </p>
                </div>

                <div className="feature-card">
                    <div className="feature-icon">🛡️</div>
                    <h3 className="feature-title">Role-Based Control</h3>
                    <p className="feature-desc">
                        Granular permissions for Admins and Operators.
                        Give users exactly the access they need, and nothing they don't.
                    </p>
                </div>

                <div className="feature-card">
                    <div className="feature-icon">📊</div>
                    <h3 className="feature-title">Live Monitoring</h3>
                    <p className="feature-desc">
                        Track active sessions, visualize message metrics, and manage
                        your fleet's health from a centralized command center.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default LandingPage;
