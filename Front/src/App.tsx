import { useState } from 'react';
import { Home } from './screens/Home';
import { Estacionar } from './screens/Estacionar';

type Screen = 'home' | 'estacionar';

function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('home');

  const handleNavigate = (screen: string) => {
    setCurrentScreen(screen as Screen);
  };

  const handleBack = () => {
    setCurrentScreen('home');
  };

  return (
    <div className="max-w-md mx-auto bg-white min-h-screen shadow-xl">
      {currentScreen === 'home' && <Home onNavigate={handleNavigate} />}
      {currentScreen === 'estacionar' && <Estacionar onBack={handleBack} />}
    </div>
  );
}

export default App;
