// server.js
// Minimal Node/Express backend for Tomis.AI
// - reads secrets from Secret Manager
// - example endpoint to call Vertex AI (text generation) using @google-cloud/aiplatform
// - example server-side Maps geocode using Maps API key from secret manager
// - Firestore usage example

const express = require('express');
const { SecretManagerServiceClient } = require('@google-cloud/secret-manager');
const { Firestore } = require('@google-cloud/firestore');
const { PredictionServiceClient } = require('@google-cloud/aiplatform').v1;
const fetch = require('node-fetch');

const app = express();
app.use(express.json());

const projectId = process.env.GCP_PROJECT || process.env.PROJECT_ID || '<REPLACE_WITH_PROJECT>';
const region = process.env.REGION || 'europe-west1';

// clients
const smClient = new SecretManagerServiceClient();
const firestore = new Firestore({projectId});
const vertexClient = new PredictionServiceClient();

async function accessSecret(secretName) {
  // secretName should be like: 'projects/PROJECT_ID/secrets/NAME/versions/latest'
  try {
    const [version] = await smClient.accessSecretVersion({ name: secretName });
    const payload = version.payload.data.toString('utf8');
    return payload;
  } catch (err) {
    console.error('Error accessing secret', secretName, err);
    throw err;
  }
}

async function getMapsKey() {
  // set env variable MAPS_SECRET_NAME to full resource name
  if(!process.env.MAPS_SECRET_NAME) throw new Error('MAPS_SECRET_NAME not set');
  return accessSecret(process.env.MAPS_SECRET_NAME);
}

// Example: server-side geocode (Maps)
app.get('/api/geocode', async (req, res) => {
  const address = req.query.address;
  if (!address) return res.status(400).json({error: 'address required'});

  try {
    const mapsKey = await getMapsKey();
    const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(address)}&key=${mapsKey}`;
    const resp = await fetch(url);
    const data = await resp.json();
    return res.json(data);
  } catch (err) {
    console.error(err);
    res.status(500).json({error: 'geocode failed'});
  }
});

// Example: Vertex AI text generation (skeleton)
app.post('/api/vertex/generate', async (req, res) => {
  // request body: { prompt: "text" }
  const prompt = req.body.prompt;
  if (!prompt) return res.status(400).json({error: 'prompt required'});

  try {
    // Model resource: for example "projects/{project}/locations/{location}/publishers/google/models/text-bison@001"
    // Replace with chosen model ID.
    const model = process.env.VERTEX_MODEL || `projects/${projectId}/locations/${region}/publishers/google/models/text-bison@001`;

    const request = {
      endpoint: `projects/${projectId}/locations/${region}`,
      instances: [
        { content: prompt }
      ],
      parameters: {}
    };

    // Using PredictionServiceClient: doPredict or predict depending on API.
    const [response] = await vertexClient.predict({
      endpoint: model, // keep model as endpoint in some client versions (see client docs)
      instances: [{content: prompt}],
      parameters: {}
    });

    // response depends on model; adapt parsing
    return res.json(response);
  } catch (err) {
    console.error('Vertex error', err);
    res.status(500).json({error: 'vertex failed', details: err.toString()});
  }
});

// Example: write/read Firestore
app.post('/api/messages', async (req, res) => {
  const { user, text } = req.body;
  if (!user || !text) return res.status(400).json({error: 'user and text required'});
  try {
    const docRef = await firestore.collection('messages').add({
      user,
      text,
      createdAt: new Date()
    });
    return res.json({ok: true, id: docRef.id});
  } catch (err) {
    console.error(err);
    res.status(500).json({error: 'firestore write failed'});
  }
});

app.get('/health', (req,res) => res.send('ok'));

const PORT = process.env.PORT || 8080;
app.listen(PORT, ()=> console.log(`Tomis backend listening on ${PORT}`));
