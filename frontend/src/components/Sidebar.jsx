import React from 'react';
import { Boxes, Zap, HardDrive, Mail, Users, MessageSquare, Video } from 'lucide-react';

const Sidebar = ({ status, onClearChat, onNewSession, apiUrl }) => {
  const integrations = [
    { name: 'Google Workspace', id: 'google', icon: <HardDrive size={16} />, authUrl: `${apiUrl}/auth/google` },
    { name: 'Notion', id: 'notion', icon: <Boxes size={16} />, authUrl: `${apiUrl}/auth/notion`  },
    { name: 'Slack', id: 'slack', icon: <Users size={16} />, authUrl: null }
  ];

  return (
    <div className="sidebar">
      <h1><Zap size={24} /> Omni Copilot</h1>
      
      <div className="bento-card" style={{flex: 1}}>
        <h2>Integrations</h2>
        <div className="integration-list">
          {integrations.map((pr) => {
            const isConnected = status?.[pr.id];
            return (
              <a 
                key={pr.id} 
                className="integration-item" 
                href={!isConnected && pr.authUrl ? pr.authUrl : '#'} 
                target={pr.authUrl ? "_blank" : "_self"} 
                rel="noreferrer"
              >
                <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                  {pr.icon} <span>{pr.name}</span>
                </div>
                <div className="integration-status">
                  <div className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></div>
                </div>
              </a>
            );
          })}
        </div>
      </div>

      <div className="bento-card">
        <h2>Session Control</h2>
        <div style={{display: 'flex', gap: '12px'}}>
          <button className="btn-secondary" style={{flex: 1}} onClick={onClearChat}>Clear Chat</button>
          <button className="btn-secondary" style={{flex: 1}} onClick={onNewSession}>New Session</button>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
