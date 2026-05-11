const { ApolloServer } = require('@apollo/server');
const { startStandaloneServer } = require('@apollo/server/standalone');

// Copernicus service URL (from environment)
const COPERNICUS_URL = process.env.COPERNICUS_SERVICE_URL || 'http://localhost:5000';

// GraphQL Schema for EU Earth Monitor
const typeDefs = `#graphql
  type SatelliteScene {
    id: ID
    title: String
    location: String
    city: String
    country: String
    imageUrl: String
    description: String
    date: String
    source: String
  }

  type EnvironmentHotspot {
    location: String
    alertCount: Int
    alertType: String
  }

  type Query {
    search(text: String): [SatelliteScene]
    getHotspots(locations: [String]): [EnvironmentHotspot]
  }
`;

// Resolvers - now call the Copernicus Python service
const resolvers = {
    Query: {
        search: async (_, { text }) => {
            console.log(`[EU Earth Monitor] Searching for: ${text}`);
            try {
                const response = await fetch(`${COPERNICUS_URL}/search?query=${encodeURIComponent(text)}`);
                const data = await response.json();

                if (data.usedMockData) {
                    console.log('[EU Earth Monitor] Using fallback mock data');
                }

                return data.scenes || [];
            } catch (error) {
                console.error('[EU Earth Monitor] Error calling Copernicus service:', error.message);
                // Return empty array on error
                return [];
            }
        },
        getHotspots: async (_, { locations }) => {
            try {
                let url = `${COPERNICUS_URL}/hotspots`;
                if (locations && locations.length > 0) {
                    const params = new URLSearchParams();
                    locations.forEach(loc => params.append('locations', loc));
                    url += `?${params.toString()}`;
                }
                const response = await fetch(url);
                const data = await response.json();
                return data.hotspots || [];
            } catch (error) {
                console.error('[EU Earth Monitor] Error fetching hotspots:', error.message);
                return [];
            }
        },
    },
};

const server = new ApolloServer({
    typeDefs,
    resolvers,
});

async function startServer() {
    const { url } = await startStandaloneServer(server, {
        listen: { port: 4000 },
    });
    console.log(`EU Earth Monitor Server ready at: ${url}`);
    console.log(`Copernicus service: ${COPERNICUS_URL}`);
}

startServer();
