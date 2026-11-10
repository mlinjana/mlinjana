export default {
  fetch(request) {
    const u = new URL(request.url);
    u.hostname = "mlinjanastudios.com"; u.protocol = "https:"; u.port = "";
    return new Response(null, { status: 301, headers: { Location: u.toString(), "Strict-Transport-Security": "max-age=31536000" } });
  },
};
