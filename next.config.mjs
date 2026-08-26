/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Em desenvolvimento, o backend roda separado (uvicorn na porta 8000,
    // já que o "vercel dev" não funciona na sua rede). Esse rewrite faz
    // o front chamar sempre "/api/..." e, por baixo dos panos, redireciona
    // pro uvicorn local. Em produção na Vercel isso não é necessário --
    // lá, "/api/*" já cai direto na função Python automaticamente.
    if (process.env.NODE_ENV === "development") {
      return [
        {
          source: "/api/:path*",
          destination: "http://localhost:8000/api/:path*",
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
