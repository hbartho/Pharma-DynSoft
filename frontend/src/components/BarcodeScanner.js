import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Html5Qrcode } from 'html5-qrcode';
import { X, Camera, ScanLine } from 'lucide-react';

const BarcodeScanner = ({ onScan, onClose }) => {
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState(null);
  const scannerRef = useRef(null);
  const html5QrCodeRef = useRef(null);
  const isClosingRef = useRef(false);

  useEffect(() => {
    // Bloquer le scroll
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    
    return () => {
      document.body.style.overflow = originalOverflow;
      stopScanner();
    };
  }, []);

  const startScanner = async () => {
    setError(null);
    setIsScanning(true);

    try {
      html5QrCodeRef.current = new Html5Qrcode("barcode-reader");
      
      await html5QrCodeRef.current.start(
        { facingMode: "environment" },
        {
          fps: 10,
          qrbox: { width: 250, height: 150 },
          aspectRatio: 1.777778
        },
        (decodedText) => {
          onScan(decodedText);
          stopScanner();
        },
        () => {}
      );
    } catch (err) {
      setError("Impossible d'accéder à la caméra. Vérifiez les permissions.");
      setIsScanning(false);
      console.error("Scanner error:", err);
    }
  };

  const stopScanner = async () => {
    if (html5QrCodeRef.current) {
      try {
        await html5QrCodeRef.current.stop();
        html5QrCodeRef.current.clear();
      } catch (err) {
        console.error("Error stopping scanner:", err);
      }
    }
    setIsScanning(false);
  };

  const handleClose = () => {
    // Éviter les fermetures multiples
    if (isClosingRef.current) return;
    isClosingRef.current = true;
    
    stopScanner();
    
    // Utiliser requestAnimationFrame pour s'assurer que le DOM est stable
    requestAnimationFrame(() => {
      onClose();
    });
  };

  const handleOverlayClick = (e) => {
    // Seulement fermer si on clique directement sur l'overlay (pas sur ses enfants)
    if (e.target === e.currentTarget) {
      e.stopPropagation();
      handleClose();
    }
  };

  const scannerContent = (
    <div 
      id="barcode-scanner-overlay"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
        zIndex: 2147483647,
      }}
      onClick={handleOverlayClick}
    >
      <div 
        style={{
          backgroundColor: 'white',
          borderRadius: '12px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          maxWidth: '28rem',
          width: '100%',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '1rem',
          borderBottom: '1px solid #e2e8f0',
          background: 'linear-gradient(to right, #0d9488, #0f766e)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'white' }}>
            <ScanLine style={{ width: '20px', height: '20px' }} />
            <h3 style={{ fontWeight: 600, margin: 0 }}>Scanner un code-barres</h3>
          </div>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              handleClose();
            }}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'white',
              padding: '0.5rem',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.2)'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <X style={{ width: '20px', height: '20px' }} />
          </button>
        </div>

        {/* Scanner Area */}
        <div style={{ padding: '1rem' }}>
          {!isScanning ? (
            <div style={{ textAlign: 'center', padding: '2rem 0' }}>
              <div style={{
                width: '80px',
                height: '80px',
                margin: '0 auto 1rem',
                backgroundColor: '#ccfbf1',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <Camera style={{ width: '40px', height: '40px', color: '#0d9488' }} />
              </div>
              <p style={{ color: '#475569', marginBottom: '1rem' }}>
                Cliquez sur le bouton ci-dessous pour activer la caméra et scanner un code-barres
              </p>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  startScanner();
                }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem 1.5rem',
                  backgroundColor: '#0d9488',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '1rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'background-color 0.2s',
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#0f766e'}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#0d9488'}
              >
                <Camera style={{ width: '18px', height: '18px' }} />
                Activer la caméra
              </button>
              {error && (
                <p style={{ marginTop: '1rem', color: '#ef4444', fontSize: '0.875rem' }}>{error}</p>
              )}
            </div>
          ) : (
            <div>
              <div 
                id="barcode-reader" 
                ref={scannerRef}
                style={{ width: '100%', borderRadius: '8px', overflow: 'hidden' }}
              />
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                fontSize: '0.875rem',
                color: '#64748b',
                marginTop: '1rem',
              }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  backgroundColor: '#22c55e',
                  borderRadius: '50%',
                  animation: 'pulse 2s infinite',
                }} />
                Scan en cours... Placez le code-barres devant la caméra
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  stopScanner();
                }}
                style={{
                  width: '100%',
                  marginTop: '1rem',
                  padding: '0.75rem 1rem',
                  backgroundColor: 'white',
                  border: '1px solid #cbd5e1',
                  borderRadius: '8px',
                  fontSize: '1rem',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s',
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f8fafc'}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'white'}
              >
                Arrêter le scan
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '1rem',
          backgroundColor: '#f8fafc',
          borderTop: '1px solid #e2e8f0',
        }}>
          <p style={{ fontSize: '0.75rem', color: '#64748b', textAlign: 'center', margin: 0 }}>
            Formats supportés: EAN-13, EAN-8, Code 128, Code 39, UPC-A, UPC-E, QR Code
          </p>
        </div>
      </div>
    </div>
  );

  return createPortal(scannerContent, document.body);
};

export default BarcodeScanner;
