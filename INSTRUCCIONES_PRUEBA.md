# Instrucciones para Pruebas Manuales del Bot

## ⚠️ IMPORTANTE ANTES DE EMPEZAR

**Binance NO funciona con VPN conectado a USA.** Antes de hacer las pruebas:

1. **Desconecta el VPN de USA** O conéctalo a otro país (Europa, Asia, Latinoamérica)
2. Verifica que tus API keys sean de **Binance TESTNET** (https://testnet.binancefuture.com)
3. Asegúrate de tener fondos USDT en tu cuenta de testnet

---

## 📋 PASO 1: Verificar Configuración

Abre el archivo `config\.env` y verifica que contenga:

```env
BINANCE_TESTNET_API_KEY=lIkTuMQxEzBJDSQbq5uLx0h0MWsAfj9GbLxfDvj5mjiDNDtWoI1RfL2AdxyWdtlr
BINANCE_TESTNET_API_SECRET=G9lKVtLL76DrI9G9p1FyA1BtaqoZxDRmqeUVZBDULhkONjEeTdKi7XtFDS3fFea2
TRADING_MODE=TESTNET
TRADING_PAIR=BTCUSDT
```

---

## 📋 PASO 2: Test de Conexión

1. **Abre una terminal/CMD** en la carpeta del proyecto:
   ```cmd
   cd C:\Users\arlex\Documents\crypto-trading-bot
   ```

2. **Activa el entorno virtual:**
   ```cmd
   venv\Scripts\activate
   ```

3. **Ejecuta el test de conexión:**
   ```cmd
   python tests\test_connection.py
   ```

---

## ✅ Qué Esperar del Test

Si todo funciona correctamente, deberías ver:

```
======================================================================
  Testing Binance Connection
======================================================================
Initializing Binance connector...
✓ Connection successful

======================================================================
  Testing Balance Retrieval
======================================================================
Total Balance:     $XXXX.XX USDT
Available Balance: $XXXX.XX USDT
✓ Balance retrieved successfully

======================================================================
  Testing Ticker Price
======================================================================
BTCUSDT Current Price: $XX,XXX.XX
✓ Ticker price retrieved successfully

======================================================================
  Testing Historical Data Retrieval
======================================================================
Fetching last 100 candles for BTCUSDT (4h)...
✓ Retrieved 100 candles

======================================================================
  Testing Market Data Processing
======================================================================
Converting klines to DataFrame...
✓ DataFrame created with 100 rows

DataFrame columns: ['open', 'high', 'low', 'close', 'volume']

Last 5 candles:
[Mostrará las últimas 5 velas]

======================================================================
  Testing Technical Indicators
======================================================================
Calculating EMAs...
✓ Indicators calculated successfully

Available indicators:
  - ema_fast
  - ema_slow
  - atr
  - volume_avg
  - rsi
  - bb_upper
  - bb_middle
  - bb_lower

Latest indicator values:
  Close Price:    $XX,XXX.XX
  EMA(9):         $XX,XXX.XX
  EMA(21):        $XX,XXX.XX
  ATR(14):        $XXX.XX
  RSI(14):        XX.XX
  Volume:         XXX,XXX.XX
  Volume Avg:     XXX,XXX.XX

======================================================================
  Testing EMA Crossover Detection
======================================================================
○ No EMA crossover at this time
(o "✓ EMA Crossover detected: BULLISH/BEARISH")

======================================================================
  Testing Position Manager
======================================================================
Calculating position size...

Position sizing for LONG trade:
  Capital:        $XXX.XX
  Entry Price:    $XX,XXX.XX
  Stop Loss:      $XX,XXX.XX (2%)
  Take Profit:    $XX,XXX.XX (6%)
  Position Size:  X.XXXXXX BTC
  Leverage:       2x
  Risk Amount:    $X.XX
  Risk/Reward:    1:3.00
✓ Position calculations successful

======================================================================
  Test Summary
======================================================================
✓ All tests passed successfully!

Your bot is ready to trade.
Mode: TESTNET
Symbol: BTCUSDT
Strategy: EMA Crossover (9/21)

*** Remember: You are in TESTNET mode ***
Use test funds to verify strategy before going live!

To start the bot, run: python main.py
======================================================================
```

---

## 📋 PASO 3: Copiar Resultados

**Por favor copia y pégame TODO el output del test**, incluyendo:
- ✅ El balance de tu cuenta de testnet
- ✅ El precio actual de BTC
- ✅ Los valores de los indicadores
- ✅ Cualquier error si lo hay

---

## 📋 PASO 4: Si el Test Pasa, Ejecutar el Bot

Si todos los tests pasaron, puedes iniciar el bot:

```cmd
python main.py
```

Verás algo como:

```
======================================================================
  CRYPTO TRADING BOT - Binance Futures
======================================================================
  Mode:          TESTNET
  Trading Pair:  BTCUSDT
  Timeframe:     4h
  Strategy:      EMA Crossover (9/21)
  Max Leverage:  2x
  Risk/Trade:    1.0%
  Stop Loss:     2.0%
  Take Profit:   6.0%
======================================================================

  *** TESTNET MODE - Using test funds ***

======================================================================

[Luego empezará a mostrar logs cada 5 minutos]
```

---

## ❌ Posibles Errores y Soluciones

### Error: "Service unavailable from a restricted location"
**Causa:** VPN conectado a USA o país bloqueado
**Solución:**
- Desconecta el VPN completamente, O
- Conéctalo a Europa, Asia, o Latinoamérica

### Error: "Invalid API-key"
**Causa:** API keys incorrectas
**Solución:**
- Verifica que las keys sean de testnet.binancefuture.com
- Regenera las keys en el testnet si es necesario

### Error: "Insufficient balance"
**Causa:** No tienes fondos en testnet
**Solución:**
- Ve a https://testnet.binancefuture.com
- Usa el botón "Get Test Funds" para obtener USDT de prueba

### Error: "Module not found"
**Causa:** Dependencias no instaladas
**Solución:**
```cmd
venv\Scripts\activate
pip install -r requirements.txt
```

---

## 📊 Qué Hacer Mientras el Bot Corre

1. **Observa los logs en consola** - Verás actualizaciones cada 5 minutos
2. **Revisa los archivos de log:**
   - `logs\trading.log` - Actividad general
   - `logs\errors.log` - Errores
   - `logs\trades.log` - Trades ejecutados

3. **Monitorea tu cuenta en Binance Testnet:**
   - https://testnet.binancefuture.com

4. **Deja correr el bot al menos 24 horas** para ver cómo se comporta

---

## 🛑 Cómo Detener el Bot

Presiona **Ctrl+C** en la terminal. El bot se detendrá de forma segura.

---

## 📝 Información a Reportarme

Después de ejecutar el test y/o el bot, por favor dame:

1. ✅ **Output completo del test** (copia y pega todo)
2. ✅ **Balance inicial** de tu cuenta testnet
3. ✅ **Cualquier error** que hayas visto
4. ✅ **Si el bot ejecutó algún trade**, los detalles del mismo
5. ✅ **Logs relevantes** de `logs\trading.log` si hay algo interesante

---

## 🎯 Objetivo del Test

El objetivo es verificar que:
- ✅ La conexión a Binance Testnet funciona
- ✅ El bot puede obtener datos de mercado
- ✅ Los indicadores técnicos se calculan correctamente
- ✅ El sistema de gestión de riesgo funciona
- ✅ El bot puede detectar señales de trading
- ✅ (Opcional) Que pueda ejecutar trades de prueba

---

## 💡 Consejos

1. **Sé paciente** - Las señales EMA crossover en 4h no ocurren constantemente
2. **Prueba en diferentes horarios** - El mercado se mueve diferente
3. **Revisa los logs** - Te ayudarán a entender qué está haciendo el bot
4. **No te preocupes** - Es dinero de prueba, experimenta libremente

---

## 🔄 Siguiente Paso

Una vez que tengas resultados del test, compártelos conmigo y podemos:
- ✅ Ajustar parámetros si es necesario
- ✅ Agregar features adicionales
- ✅ Preparar para backtesting
- ✅ Eventualmente mover a producción (con mucho cuidado)

---

¡Buena suerte con las pruebas! 🚀
