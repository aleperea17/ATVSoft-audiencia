import { useState } from "react";
import { LoginError, login } from "../api";
import logo from "../assets/atv-logo.svg";
import styles from "./Login.module.css";

export default function Login({ onSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      await login(username, password);
      await onSuccess();
    } catch (err) {
      setError(err instanceof LoginError ? err.message : "No se pudo iniciar sesión.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className={styles.screen}>
      <img className={styles.logo} src={logo} alt="ATV" />
      <form className={styles.card} onSubmit={onSubmit}>
        <h1 className={styles.title}>Iniciar sesion</h1>
        <label className={styles.label} htmlFor="usuario">
          USUARIO
        </label>
        <input
          id="usuario"
          className={styles.input}
          name="username"
          autoComplete="username"
          placeholder="tu_usuario"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
        <label className={styles.label} htmlFor="contrasena">
          CONTRASENA
        </label>
        <input
          id="contrasena"
          className={styles.input}
          name="password"
          type="password"
          autoComplete="current-password"
          placeholder="Minimo 6 caracteres"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <button className={styles.submit} type="submit" disabled={pending}>
          INICIAR SESION
        </button>
        {error ? <p className={styles.error}>{error}</p> : null}
      </form>
    </main>
  );
}
