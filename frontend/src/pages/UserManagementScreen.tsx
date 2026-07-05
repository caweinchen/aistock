import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { ArrowLeft, ShieldCheck, UserCheck, UserX } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { getUsers, updateUser } from '../services/api';
import type { AppUser } from '../types';

interface UserManagementScreenProps {
  isAdmin: boolean;
  onBack: () => void;
}

export function UserManagementScreen({ isAdmin, onBack }: UserManagementScreenProps) {
  const [users, setUsers] = useState<AppUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [updatingUserId, setUpdatingUserId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadUsers = async () => {
    if (!isAdmin) {
      setError('No permission to access user management');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      setUsers(await getUsers());
    } catch {
      setError('Failed to load users');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadUsers();
  }, [isAdmin]);

  const handleUpdateUser = async (userId: number, patch: Partial<Pick<AppUser, 'is_active' | 'role'>>) => {
    setUpdatingUserId(userId);
    setError(null);
    try {
      const updated = await updateUser(userId, patch);
      setUsers((current) => current.map((user) => (user.id === userId ? updated : user)));
    } catch {
      setError('Failed to update user');
    } finally {
      setUpdatingUserId(null);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.centerPanel}>
        <ActivityIndicator color="#0F8B8D" />
        <Text style={styles.subtleText}>Loading users</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Pressable style={styles.backButton} onPress={onBack}>
          <ArrowLeft size={20} color="#162033" />
        </Pressable>
        <View>
          <Text style={styles.title}>User Management</Text>
          <Text style={styles.subtleText}>Approve registered users and manage roles</Text>
        </View>
        <ShieldCheck size={24} color="#0F8B8D" />
      </View>

      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      <View style={styles.userList}>
        {users.map((user) => {
          const isUpdating = updatingUserId === user.id;
          return (
            <View key={user.id} style={styles.userRow}>
              <View style={styles.userInfo}>
                <Text style={styles.username}>{user.username}</Text>
                <View style={styles.badgeLine}>
                  <Text style={[styles.badge, user.is_active ? styles.activeBadge : styles.inactiveBadge]}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </Text>
                  <Text style={[styles.badge, user.role === 'admin' ? styles.adminBadge : styles.userBadge]}>
                    {user.role === 'admin' ? 'Admin' : 'User'}
                  </Text>
                </View>
              </View>

              <View style={styles.actions}>
                <Pressable
                  style={[styles.iconButton, user.is_active ? styles.dangerButton : styles.primaryButton]}
                  disabled={isUpdating}
                  onPress={() => handleUpdateUser(user.id, { is_active: !user.is_active })}
                >
                  {user.is_active ? <UserX size={16} color="#FFFFFF" /> : <UserCheck size={16} color="#FFFFFF" />}
                  <Text style={styles.buttonText}>{user.is_active ? 'Disable' : 'Enable'}</Text>
                </Pressable>
                <Pressable
                  style={[styles.iconButton, styles.secondaryButton]}
                  disabled={isUpdating}
                  onPress={() => handleUpdateUser(user.id, { role: user.role === 'admin' ? 'user' : 'admin' })}
                >
                  <ShieldCheck size={16} color="#0F8B8D" />
                  <Text style={styles.secondaryButtonText}>{user.role === 'admin' ? 'Make User' : 'Make Admin'}</Text>
                </Pressable>
              </View>
            </View>
          );
        })}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { gap: 14, padding: 20, paddingBottom: 36 },
  centerPanel: {
    alignItems: 'center',
    flex: 1,
    gap: 10,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'space-between',
  },
  backButton: {
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    height: 40,
    justifyContent: 'center',
    width: 40,
  },
  title: { color: '#162033', fontSize: 22, fontWeight: '800' },
  subtleText: { color: '#6B7280', fontSize: 13 },
  errorText: { color: '#B42318', fontSize: 13 },
  userList: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    overflow: 'hidden',
  },
  userRow: {
    borderBottomColor: '#EEF2F7',
    borderBottomWidth: 1,
    gap: 12,
    padding: 14,
  },
  userInfo: { gap: 8 },
  username: { color: '#162033', fontSize: 16, fontWeight: '800' },
  badgeLine: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  badge: {
    borderRadius: 8,
    fontSize: 12,
    fontWeight: '700',
    overflow: 'hidden',
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  activeBadge: { backgroundColor: '#ECFDF3', color: '#047857' },
  inactiveBadge: { backgroundColor: '#FEF3F2', color: '#B42318' },
  adminBadge: { backgroundColor: '#E9FBF7', color: '#0F766E' },
  userBadge: { backgroundColor: '#F3F4F6', color: '#4B5563' },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  iconButton: {
    alignItems: 'center',
    borderRadius: 8,
    flexDirection: 'row',
    gap: 6,
    minHeight: 36,
    paddingHorizontal: 10,
  },
  primaryButton: { backgroundColor: '#0F8B8D' },
  dangerButton: { backgroundColor: '#B42318' },
  secondaryButton: { backgroundColor: '#E9FBF7' },
  buttonText: { color: '#FFFFFF', fontSize: 13, fontWeight: '800' },
  secondaryButtonText: { color: '#0F8B8D', fontSize: 13, fontWeight: '800' },
});
