/**
 * Composant Footer avec branding DynSoft Pharma + version (dernière release GitHub, sinon version applicative)
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import pkg from '../../package.json';

const Footer = () => {
  const { data } = useQuery({
    queryKey: ['app-version'],
    queryFn: async () => (await api.get('/version')).data,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
  const release = data?.release;
  const label = release?.tag || `v${data?.app_version || pkg.version}`;
  const title = release?.published_at
    ? `Release GitHub ${release.tag} publiée le ${new Date(release.published_at).toLocaleDateString('fr-FR')}`
    : 'Version de l\'application';

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
        {release?.url ? (
          <a href={release.url} target="_blank" rel="noreferrer" title={title} style={{ color: '#64748b', marginLeft: 8, textDecoration: 'none' }} data-testid="app-version">{label}</a>
        ) : (
          <span title={title} style={{ color: '#64748b', marginLeft: 8 }} data-testid="app-version">{label}</span>
        )}
      </p>
    </div>
  );
};

export default Footer;
