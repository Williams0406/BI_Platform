"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import PublicOnly from "@/components/auth/PublicOnly";
import Alert from "@/components/ui/Alert";
import { ROUTES } from "@/lib/constants/routes";
import { useAuth } from "@/lib/hooks/useAuth";
import { getApiErrorMessage } from "@/lib/utils/errors";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handleChange(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await login(form);
      router.replace(ROUTES.APP);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "No se pudo iniciar sesión."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PublicOnly>
      <main className="authPage">
        <section className="authPanel authIntro">
          <div className="brandMark brandMarkLarge">BI</div>
          <p className="eyebrow">BUSINESS INTELLIGENCE PLATFORM</p>
          <h1>Datos, inteligencia y decisión en un mismo entorno.</h1>
          <p>
            Esta primera versión prioriza la lógica funcional. Los módulos se habilitarán progresivamente
            durante las siguientes fases.
          </p>
        </section>

        <section className="authPanel authFormPanel">
          <form className="authForm" onSubmit={handleSubmit}>
            <div>
              <p className="eyebrow">ACCESO</p>
              <h2>Iniciar sesión</h2>
              <p className="muted">Usa el correo registrado en el backend Django.</p>
            </div>

            <Alert>{error}</Alert>

            <label className="field">
              <span>Correo electrónico</span>
              <input
                autoComplete="email"
                name="email"
                onChange={handleChange}
                placeholder="usuario@empresa.com"
                required
                type="email"
                value={form.email}
              />
            </label>

            <label className="field">
              <span>Contraseña</span>
              <input
                autoComplete="current-password"
                minLength={8}
                name="password"
                onChange={handleChange}
                required
                type="password"
                value={form.password}
              />
            </label>

            <button className="button buttonPrimary buttonBlock" disabled={submitting} type="submit">
              {submitting ? "Ingresando..." : "Ingresar"}
            </button>

            <p className="authFooterText">
              ¿Aún no tienes cuenta? <Link href={ROUTES.REGISTER}>Crear cuenta</Link>
            </p>
          </form>
        </section>
      </main>
    </PublicOnly>
  );
}
