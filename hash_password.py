from werkzeug.security import generate_password_hash

if __name__ == '__main__':
    raw = 'admin123'
    h   = generate_password_hash(raw, method='pbkdf2:sha256', salt_length=8)
    print('Usa este hash para tu BD:\n', h)
