import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './screens/Home';
import Estacionar from './screens/Estacionar';
import Emergencia from './screens/Emergencia';
import Salir from './screens/Salir';
import ResolverAhora from './screens/ResolverAhora';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 flex justify-center">
        <div className="w-full max-w-md bg-white min-h-screen relative shadow-lg">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/estacionar" element={<Estacionar />} />
            <Route path="/emergencia" element={<Emergencia />} />
            <Route path="/salir" element={<Salir />} />
            <Route path="/resolver-ahora" element={<ResolverAhora />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
