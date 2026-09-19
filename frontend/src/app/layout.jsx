import "./globals.css";

import { AuthProvider } from "@/lib/context/AuthContext";
import { WorkspaceProvider } from "@/lib/context/WorkspaceContext";

export const metadata = {
  title: "Business Intelligence Platform",
  description: "Data, BI, Data Science and Optimization platform",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body>
        <AuthProvider>
          <WorkspaceProvider>{children}</WorkspaceProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
