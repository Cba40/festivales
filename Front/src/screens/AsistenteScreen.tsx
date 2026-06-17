import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { 
  UtensilsCrossed, Car, Bath, Armchair, Trees, 
  Send, Trash2, AlertTriangle, Bus, LogOut, Info, RefreshCw, Compass
} from 'lucide-react';
import { useAppStore } from '@/core/state/store';
import axios from 'axios';

interface Message {
  id: string;
  role: 'user' | 'bot';
  text: string;
  timestamp: Date;
}

const chips = [
  { label: '¿Dónde comer?', icon: UtensilsCrossed },
  { label: '¿Dónde estacionar?', icon: Car },
  { label: '¿Dónde hay baños?', icon: Bath },
  { label: '¿Qué zona tiene menos gente?', icon: Trees },
  { label: '¿Dónde descansar?', icon: Armchair },
];

const AsistenteScreen = () => {
  const navigate = useNavigate();
  const userLocation = useAppStore((state) => state.userLocation);
  const requestLocation = useAppStore((state) => state.requestLocation);

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [usingFallback, setUsingFallback] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const CLIENT_KEY = 'cbai_client_festival-jesus-maria';
  const STORAGE_KEY = 'cbai_messages_festival-jesus-maria';
  const FALLBACK_KEY = 'cbai_using_fallback_mode';

  // Obtener o crear Client ID
  const getClientId = (): string => {
    let id = localStorage.getItem(CLIENT_KEY);
    if (!id) {
      id = 'widget_' + Math.random().toString(36).substring(2, 18);
      localStorage.setItem(CLIENT_KEY, id);
    }
    return id;
  };

  // Cargar historial inicial al montar
  useEffect(() => {
    // Intentar pedir ubicación al entrar para dar recomendaciones precisas
    requestLocation();

    // Cargar fallback status
    const wasFallback = localStorage.getItem(FALLBACK_KEY) === 'true';
    setUsingFallback(wasFallback);

    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as any[];
        setMessages(
          parsed.map((m) => ({
            ...m,
            timestamp: new Date(m.timestamp),
          }))
        );
      } catch (e) {
        initializeGreeting(wasFallback);
      }
    } else {
      initializeGreeting(wasFallback);
    }
  }, []);

  // Guardar mensajes cuando cambian
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    }
  }, [messages]);

  // Scroll al final
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const initializeGreeting = (isFallbackMode: boolean) => {
    const greetingText = isFallbackMode
      ? '¡Hola! Soy CBAi, tu asistente de pruebas (cba-4-0). Estoy listo para ayudarte con consultas generales sobre nuestros servicios. ¿En qué te puedo ayudar hoy?'
      : '¡Hola! Soy CBAi, el asistente virtual del Festival de Jesús María 2026. Te puedo ayudar a encontrar estacionamientos, baños, paradas de transporte, lugares para comer, salidas y hospedajes del festival. ¿En qué te puedo ayudar?';

    setMessages([
      {
        id: 'welcome',
        role: 'bot',
        text: greetingText,
        timestamp: new Date(),
      },
    ]);
  };

  const handleClearChat = () => {
    localStorage.removeItem(STORAGE_KEY);
    initializeGreeting(usingFallback);
  };

  const sendMessageToBot = async (textToSend: string, forceFallback = false) => {
    if (!textToSend.trim() || isLoading) return;

    const userMsg: Message = {
      id: Math.random().toString(36).substring(2, 11),
      role: 'user',
      text: textToSend,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsLoading(true);

    const clientId = getClientId();
    const activeFallback = forceFallback || usingFallback;
    const tenantSlug = activeFallback ? 'cba-4-0' : 'festival-jesus-maria';

    const chatbotBaseUrl = import.meta.env.VITE_CHATBOT_API_URL || 'https://cbachat.vercel.app';
    const chatbotUrl = `${chatbotBaseUrl}/api/v1/widget/chat/`;

    try {
      const response = await axios.post(chatbotUrl, {
        tenant_slug: tenantSlug,
        message: textToSend,
        client_id: clientId,
        latitude: userLocation ? userLocation[0] : null,
        longitude: userLocation ? userLocation[1] : null,
      });

      const botReplyText = response.data?.response || 'Disculpa, no obtuve respuesta.';
      
      const botMsg: Message = {
        id: Math.random().toString(36).substring(2, 11),
        role: 'bot',
        text: botReplyText,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (error: any) {
      console.warn('Error en la API del chatbot:', error);

      // Si falla con 404 (tenant no encontrado) y no estábamos usando fallback, intentamos activar el fallback automáticamente
      if (error?.response?.status === 404 && !activeFallback) {
        console.log('Activando fallback al tenant cba-4-0...');
        setUsingFallback(true);
        localStorage.setItem(FALLBACK_KEY, 'true');
        
        // Agregar un mensaje del sistema indicando el cambio temporal
        const systemNotice: Message = {
          id: 'sys-' + Math.random().toString(36).substring(2, 11),
          role: 'bot',
          text: '⚠️ El tenant "festival-jesus-maria" no se encuentra activo en producción. Redirigiendo la consulta automáticamente al asistente de pruebas (cba-4-0)...',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, systemNotice]);

        // Reintentar la consulta con el fallback activo
        await sendMessageToBot(textToSend, true);
        return;
      }

      // En caso de otro error
      const errorMsg: Message = {
        id: Math.random().toString(36).substring(2, 11),
        role: 'bot',
        text: 'Lo siento, hubo un error de conexión al procesar tu mensaje. Por favor, verifica tu internet e intenta nuevamente.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = () => {
    if (inputText.trim()) {
      sendMessageToBot(inputText);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  // Parser de texto para renderizar enlaces Markdown como botones interactivos
  const renderMessageText = (text: string) => {
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;

    while ((match = linkRegex.exec(text)) !== null) {
      const matchIndex = match.index;
      
      // Añadir texto plano previo al enlace
      if (matchIndex > lastIndex) {
        parts.push(<span key={`txt-${matchIndex}`}>{text.substring(lastIndex, matchIndex)}</span>);
      }

      const linkText = match[1];
      const linkPath = match[2];

      // Seleccionar un icono representativo del enlace
      let LinkIcon = Compass;
      if (linkPath.includes('comer')) LinkIcon = UtensilsCrossed;
      else if (linkPath.includes('estacionar')) LinkIcon = Car;
      else if (linkPath.includes('transporte')) LinkIcon = Bus;
      else if (linkPath.includes('pernoctar')) LinkIcon = Info;
      else if (linkPath.includes('emergencia')) LinkIcon = AlertTriangle;
      else if (linkPath.includes('salir')) LinkIcon = LogOut;

      parts.push(
        <button
          key={`btn-${matchIndex}`}
          onClick={() => navigate(linkPath)}
          className="inline-flex items-center gap-1.5 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 text-blue-600 dark:text-blue-300 font-bold text-xs px-3 py-1.5 rounded-xl border border-blue-200/50 dark:border-blue-800/40 shadow-sm mx-1 my-1 transition-all hover:scale-102 active:scale-98"
        >
          <LinkIcon size={13} className="flex-shrink-0" />
          {linkText}
        </button>
      );

      lastIndex = linkRegex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(<span key="txt-end">{text.substring(lastIndex)}</span>);
    }

    return parts.length > 0 ? <div className="space-y-1">{parts}</div> : text;
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col h-screen overflow-hidden">
      <Header title="Asistente rápido" showBack onBack={() => navigate('/')} />

      {/* Alerta de fallback activa para testing local/desarrollo */}
      {usingFallback && (
        <div className="bg-amber-500/10 border-b border-amber-500/20 px-4 py-2 text-xs text-amber-700 dark:text-amber-400 flex items-center justify-between gap-3 shadow-inner">
          <div className="flex items-center gap-2">
            <AlertTriangle size={14} className="flex-shrink-0 text-amber-500" />
            <span className="font-medium leading-tight">
              Modo Test: Usando mente de pruebas (cba-4-0). Ejecuta el sembrado en producción para activar la mente del festival.
            </span>
          </div>
          <button 
            onClick={() => {
              setUsingFallback(false);
              localStorage.removeItem(FALLBACK_KEY);
              handleClearChat();
            }}
            className="flex items-center gap-1 bg-amber-500/20 hover:bg-amber-500/30 px-2 py-1 rounded-md text-[10px] uppercase font-bold tracking-wider transition-colors"
            title="Reintentar tenant original"
          >
            <RefreshCw size={10} /> Reintentar
          </button>
        </div>
      )}

      {/* Indicador de estado de ubicación GPS */}
      {userLocation && (
        <div className="bg-emerald-500/10 border-b border-emerald-500/20 px-4 py-1 text-[11px] text-emerald-700 dark:text-emerald-400 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="font-medium">
            GPS Activo. El bot te recomendará servicios cercanos en tiempo real.
          </span>
        </div>
      )}

      {/* Contenedor principal de mensajes */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.role === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            <div
              className={`max-w-[85%] px-4 py-3 rounded-2xl shadow-sm text-sm ${
                msg.role === 'user'
                  ? 'bg-primary text-white rounded-tr-none'
                  : 'bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-100 rounded-tl-none border border-slate-100 dark:border-slate-700/50'
              }`}
            >
              {msg.role === 'bot' ? renderMessageText(msg.text) : msg.text}
            </div>
            <span className="text-[10px] text-gray-400 dark:text-gray-500 mt-1 px-1">
              {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        ))}

        {/* Indicador de escritura */}
        {isLoading && (
          <div className="flex flex-col items-start">
            <div className="bg-white dark:bg-slate-800 px-5 py-3.5 rounded-2xl rounded-tl-none border border-slate-100 dark:border-slate-700/50 shadow-sm flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 bg-primary/40 dark:bg-primary-foreground/30 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2.5 h-2.5 bg-primary/40 dark:bg-primary-foreground/30 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2.5 h-2.5 bg-primary/40 dark:bg-primary-foreground/30 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Barra inferior de entrada y sugerencias */}
      <div className="bg-white dark:bg-slate-800 border-t border-slate-100 dark:border-slate-700/50 p-3 pb-safe">
        {/* Sugerencias Rápidas (Chips) */}
        <div className="flex gap-2 overflow-x-auto pb-3 px-1 scrollbar-none">
          {chips.map((chip) => {
            const Icon = chip.icon;
            return (
              <button
                key={chip.label}
                onClick={() => sendMessageToBot(chip.label)}
                disabled={isLoading}
                className="flex items-center gap-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600/80 px-3.5 py-2 rounded-full text-xs font-semibold text-slate-700 dark:text-slate-200 transition-all active:scale-95 flex-shrink-0 disabled:opacity-50"
              >
                <Icon size={14} className="text-slate-500 dark:text-slate-400" />
                <span>{chip.label}</span>
              </button>
            );
          })}
        </div>

        {/* Input y Botones de acción */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleClearChat}
            disabled={isLoading}
            className="p-3 bg-red-50 hover:bg-red-100 dark:bg-red-950/20 dark:hover:bg-red-950/40 text-red-600 dark:text-red-400 rounded-xl transition-colors disabled:opacity-50"
            title="Limpiar conversación"
          >
            <Trash2 size={20} />
          </button>
          
          <div className="flex-1 relative flex items-center">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder="Escribe tu consulta sobre el festival..."
              className="w-full bg-slate-100 dark:bg-slate-900 border-none outline-none focus:ring-2 focus:ring-primary/20 dark:focus:ring-primary/40 rounded-xl py-3.5 pl-4 pr-12 text-sm text-gray-800 dark:text-gray-100 transition-all placeholder:text-gray-400 dark:placeholder:text-gray-500 disabled:opacity-75"
            />
            <button
              onClick={handleSend}
              disabled={!inputText.trim() || isLoading}
              className="absolute right-2 p-2 bg-primary hover:bg-primary/95 text-white rounded-lg transition-colors disabled:bg-gray-300 dark:disabled:bg-slate-700 disabled:text-gray-400 dark:disabled:text-slate-500"
              aria-label="Enviar mensaje"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AsistenteScreen;
