/**
 * Composant Footer avec branding DynSoft Pharma
 */

import React from 'react';

const Footer = () => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '12px 16px',
        borderTop: '1px solid #e2e8f0',
        backgroundColor: '#f8fafc',
        marginTop: 'auto',
      }}
    >
      <img
        style={{ width: '20px', height: '20px', marginRight: '8px' }}
        src={require('../images/logo.jpg')}
        alt="DynSoft Pharma Logo"
      />
      <p
        style={{
          color: '#000000',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif',
          fontSize: '12px',
          alignItems: 'center',
          marginBottom: 0,
          margin: 0,
        }}
      >
        Made by DynSoft Pharma
      </p>
    </div>
  );
};

export default Footer;
