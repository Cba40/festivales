import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './screens/Home';
import Estacionar from './screens/Estacionar';
import Emergencia from './screens/Emergencia';
import Salir from './screens/Salir';
import ResolverAhora from './screens/ResolverAhora';
import Servicios from './screens/Servicios';
import ServiciosTransporte from './screens/ServiciosTransporte';
import ServiciosComer from './screens/ServiciosComer';
import ServiciosGenerales from './screens/ServiciosGenerales';
import Pernoctar from './screens/Pernoctar';

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
            <Route path="/servicios" element={<Servicios />} />
            <Route path="/servicios/transporte" element={<ServiciosTransporte />} />
            <Route path="/servicios/comer" element={<ServiciosComer />} />
            <Route path="/servicios/generales" element={<ServiciosGenerales />} />
            <Route path="/pernoctar" element={<Pernoctar />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
